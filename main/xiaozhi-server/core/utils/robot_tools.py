"""Bounds for the five robot tools in the research specification."""
ROBOT_TOOLS={
 'self.led.set_mode':{'led':('left','right','both'),'mode':('off','on','blink_slow','blink_fast','breathe')},
 'self.robot.move':{'direction':('forward','backward','left','right','stop'),'duration_ms':(0,2000)},
 'self.robot.set_servo':{'part':('neck','arm_left','arm_right'),'angle':(0,180)},
 'self.robot.get_distance':{},'self.robot.wave_hand':{'which':('left','right','both'),'times':(1,10)}}
def validate_robot_arguments(name,arguments):
    fields=ROBOT_TOOLS.get(name)
    if fields is None:return
    if set(arguments)!=set(fields):raise ValueError('Tham số robot thiếu hoặc thừa trường')
    for key,spec in fields.items():
        value=arguments[key]
        if isinstance(spec[0] if spec else None,int):
            if type(value)!=int or not spec[0]<=value<=spec[1]:raise ValueError('Tham số robot ngoài giới hạn: '+key)
        elif value not in spec:raise ValueError('Tham số robot không hợp lệ: '+key)
