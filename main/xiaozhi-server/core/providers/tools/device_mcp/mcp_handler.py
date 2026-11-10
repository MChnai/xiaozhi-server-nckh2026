"""设备端MCP客户端支持模块"""

import json
import asyncio
import re
from core.utils.util import get_vision_url
from core.utils.auth import AuthToken
from config.logger import setup_logging
from .mcp_client import MCPClient
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

async def send_mcp_message(conn: "ConnectionHandler", payload: dict):
    """Helper to send MCP messages, encapsulating common logic."""
    if not conn.features.get("mcp"):
        logger.bind(tag=TAG).warning("客户端不支持MCP，无法发送MCP消息")
        return

    message = json.dumps({"type": "mcp", "payload": payload})

    try:
        await conn.websocket.send(message)
        logger.bind(tag=TAG).debug(f"Đã gửi MCP {payload.get('method','response')} id={payload.get('id')}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"Không gửi được MCP: {type(e).__name__}")
        raise


async def handle_mcp_message(
    conn: "ConnectionHandler", mcp_client: MCPClient, payload: dict
):
    """处理MCP消息,包括初始化、工具列表和工具调用响应等"""
    logger.bind(tag=TAG).debug(f"处理MCP消息: {str(payload)[:100]}")

    if not isinstance(payload, dict):
        logger.bind(tag=TAG).error("MCP消息缺少payload字段或格式错误")
        return

    # Handle result
    if "result" in payload:
        result = payload["result"]
        msg_id = int(payload.get("id", 0))

        # Check for tool call response first
        if msg_id in mcp_client.call_results:
            logger.bind(tag=TAG).debug(
                f"收到工具调用响应，ID: {msg_id}, 结果: {result}"
            )
            await mcp_client.resolve_call_result(msg_id, result)
            return

        if msg_id == 1:  # mcpInitializeID
            logger.bind(tag=TAG).debug("收到MCP初始化响应")
            server_info = result.get("serverInfo")
            if isinstance(server_info, dict):
                name = server_info.get("name")
                version = server_info.get("version")
                logger.bind(tag=TAG).debug(
                    f"客户端MCP服务器信息: name={name}, version={version}"
                )
            await send_mcp_message(conn,{"jsonrpc":"2.0","method":"notifications/initialized"})
            return

        elif msg_id == 2:  # mcpToolsListID
            logger.bind(tag=TAG).debug("收到MCP工具列表响应")
            if isinstance(result, dict) and "tools" in result:
                tools_data = result["tools"]
                if not isinstance(tools_data, list):
                    logger.bind(tag=TAG).error("工具列表格式错误")
                    return

                logger.bind(tag=TAG).info(
                    f"客户端设备支持的工具数量: {len(tools_data)}"
                )

                for i, tool in enumerate(tools_data):
                    if not isinstance(tool, dict):
                        continue

                    name = tool.get("name", "")
                    description = tool.get("description", "")
                    input_schema = {"type": "object", "properties": {}, "required": []}

                    if "inputSchema" in tool and isinstance(tool["inputSchema"], dict):
                        schema = tool["inputSchema"]
                        input_schema["type"] = schema.get("type", "object")
                        input_schema["properties"] = schema.get("properties", {})
                        input_schema["required"] = [
                            s for s in schema.get("required", []) if isinstance(s, str)
                        ]

                    new_tool = {
                        "name": name,
                        "description": description,
                        "inputSchema": input_schema,
                    }
                    await mcp_client.add_tool(new_tool)
                    logger.bind(tag=TAG).debug(f"客户端工具 #{i+1}: {name}")

                # 替换所有工具描述中的工具名称
                for tool_data in mcp_client.tools.values():
                    if "description" in tool_data:
                        description = tool_data["description"]
                        # 遍历所有工具名称进行替换
                        for (
                            sanitized_name,
                            original_name,
                        ) in mcp_client.name_mapping.items():
                            description = description.replace(
                                original_name, sanitized_name
                            )
                        tool_data["description"] = description

                next_cursor = result.get("nextCursor", "")
                if next_cursor:
                    logger.bind(tag=TAG).debug(f"有更多工具，nextCursor: {next_cursor}")
                    await send_mcp_tools_list_continue_request(conn, next_cursor)
                else:
                    await mcp_client.set_ready(True)
                    logger.bind(tag=TAG).debug("所有工具已获取，MCP客户端准备就绪")

                    # 刷新工具缓存，确保MCP工具被包含在函数列表中
                    if hasattr(conn, "func_handler") and conn.func_handler:
                        conn.func_handler.tool_manager.refresh_tools()
                        conn.func_handler.current_support_functions()
            return

    # Handle method calls (requests from the client)
    elif "method" in payload:
        method = payload["method"]
        logger.bind(tag=TAG).info(f"收到MCP客户端请求: {method}")

    elif "error" in payload:
        error_data = payload["error"]
        error_msg = error_data.get("message", "未知错误")
        logger.bind(tag=TAG).error(f"收到MCP错误响应: {error_msg}")

        msg_id = int(payload.get("id", 0))
        if msg_id in mcp_client.call_results:
            await mcp_client.reject_call_result(
                msg_id, Exception(f"MCP错误: {error_msg}")
            )


async def send_mcp_initialize_message(conn: "ConnectionHandler"):
    """发送MCP初始化消息"""

    vision_url = get_vision_url(conn.config)

    # 密钥生成token
    auth = AuthToken(conn.config["server"]["auth_key"])
    token = auth.generate_token(conn.headers.get("device-id"))

    vision = {
        "url": vision_url,
        "token": token,
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,  # mcpInitializeID
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
                "vision": vision,
            },
            "clientInfo": {
                "name": "XiaozhiClient",
                "version": "1.0.0",
            },
        },
    }
    logger.bind(tag=TAG).debug("发送MCP初始化消息")
    await send_mcp_message(conn, payload)


async def send_mcp_tools_list_request(conn: "ConnectionHandler"):
    """发送MCP工具列表请求"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID
        "method": "tools/list",
    }
    logger.bind(tag=TAG).debug("发送MCP工具列表请求")
    await send_mcp_message(conn, payload)


async def send_mcp_tools_list_continue_request(conn: "ConnectionHandler", cursor: str):
    """发送带有cursor的MCP工具列表请求"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID (same ID for continuation)
        "method": "tools/list",
        "params": {"cursor": cursor},
    }
    logger.bind(tag=TAG).info(f"发送带cursor的MCP工具列表请求: {cursor}")
    await send_mcp_message(conn, payload)


async def call_mcp_tool(conn,mcp_client,tool_name,args="{}",timeout=30):
    """Call an advertised tool and always release its response future."""
    if not conn.features.get('mcp') or not await mcp_client.is_ready():raise RuntimeError('Thiết bị chưa sẵn sàng MCP')
    if not mcp_client.has_tool(tool_name):raise ValueError('Thiết bị không công bố công cụ này')
    try:arguments=json.loads(args) if isinstance(args,str) and args.strip() else {} if isinstance(args,str) else args
    except json.JSONDecodeError as exc:raise ValueError('Tham số công cụ phải là JSON hợp lệ') from exc
    if not isinstance(arguments,dict):raise ValueError('Tham số công cụ phải là object')
    actual_name=mcp_client.name_mapping.get(tool_name,tool_name)
    from core.utils.robot_tools import validate_robot_arguments
    validate_robot_arguments(actual_name,arguments)
    call_id=await mcp_client.get_next_id();future=asyncio.get_running_loop().create_future()
    await mcp_client.register_call_result_future(call_id,future)
    try:
        await send_mcp_message(conn,{'jsonrpc':'2.0','id':call_id,'method':'tools/call','params':{'name':actual_name,'arguments':arguments}})
        result=await asyncio.wait_for(future,timeout=timeout)
        if isinstance(result,dict):
            if result.get('isError') is True:raise RuntimeError('Thiết bị báo thực thi công cụ thất bại')
            content=result.get('content')
            if isinstance(content,list) and content and isinstance(content[0],dict) and 'text' in content[0]:return content[0]['text']
        return json.dumps(result,ensure_ascii=False)
    except asyncio.TimeoutError as exc:raise TimeoutError('Thiết bị chưa phản hồi công cụ trong thời gian chờ; chưa xác nhận thực thi') from exc
    finally:await mcp_client.cleanup_call_result(call_id)
