package xiaozhi.modules.config.init;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.sys.service.SysParamsService;

@Component
@ConditionalOnProperty(name = "nckh.bootstrap.enabled", havingValue = "true")
public class NckhBootstrap implements ApplicationRunner {
    private final Environment env;
    private final SysParamsService params;
    private final RedisUtils redis;

    public NckhBootstrap(Environment env, SysParamsService params, RedisUtils redis) {
        this.env = env;
        this.params = params;
        this.redis = redis;
    }

    @Override
    public void run(ApplicationArguments args) {
        String host = env.getRequiredProperty("nckh.public-host");
        String secret = env.getRequiredProperty("nckh.server-secret");
        if (!host.matches("[A-Za-z0-9.-]+") || secret.length() < 32) {
            throw new IllegalStateException("NCKH_PUBLIC_HOST hoặc NCKH_SERVER_SECRET không hợp lệ");
        }
        params.updateValueByCode("server.secret", secret);
        params.updateValueByCode("server.websocket", "ws://" + host + ":8000/nckh/v1/");
        params.updateValueByCode("server.ota", "http://" + host + ":8002/nckhsv/ota/");
        params.updateValueByCode("server.fronted_url", "http://" + host + ":8002");
        for(String id:java.util.List.of("TTS_NCKH","Intent_NCKH","Memory_nomem","TTS_PIPER_NCKH","TTS_VIENEU_NCKH")){
            redis.delete(RedisKeys.getModelConfigById(id));redis.delete(RedisKeys.getModelNameById(id));
        }
        redis.delete(RedisKeys.getServerConfigKey());
    }
}
