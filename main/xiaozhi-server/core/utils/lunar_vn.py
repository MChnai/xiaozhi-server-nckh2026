"""Vietnamese civil lunar calendar, UTC+7, 1900–2099.
Astronomical method: Ho Ngoc Duc, Computing the Vietnamese lunar calendar.
Implements new moon / solar longitude formulae, not the Chinese UTC+8 calendar.
"""
import math
from datetime import date
PI=math.pi

def julian(d):
    a=(14-d.month)//12; y=d.year+4800-a; m=d.month+12*a-3
    return d.day+(153*m+2)//5+365*y+y//4-y//100+y//400-32045

def new_moon(k):
    t=k/1236.85; t2=t*t; t3=t2*t; r=PI/180
    jd=2415020.75933+29.53058868*k+0.0001178*t2-0.000000155*t3
    jd+=0.00033*math.sin((166.56+132.87*t-0.009173*t2)*r)
    m=359.2242+29.10535608*k-0.0000333*t2-0.00000347*t3
    mp=306.0253+385.81691806*k+0.0107306*t2+0.00001236*t3
    f=21.2964+390.67050646*k-0.0016528*t2-0.00000239*t3
    c=(0.1734-0.000393*t)*math.sin(m*r)+0.0021*math.sin(2*m*r)
    c-=0.4068*math.sin(mp*r)-0.0161*math.sin(2*mp*r)
    c-=0.0004*math.sin(3*mp*r)
    c+=0.0104*math.sin(2*f*r)-0.0051*math.sin((m+mp)*r)
    c-=0.0074*math.sin((m-mp)*r)-0.0004*math.sin((2*f+m)*r)
    c-=0.0004*math.sin((2*f-m)*r)+0.0006*math.sin((2*f+mp)*r)
    c+=0.0010*math.sin((2*f-mp)*r)+0.0005*math.sin((2*mp+m)*r)
    dt=(0.001+0.000839*t+0.0002261*t2-0.00000845*t3-0.000000081*t*t3) if t < -11 else (-0.000278+0.000265*t+0.000262*t2)
    return math.floor(jd+c-dt+0.5+7/24)

def sun_sector(jd):
    t=(jd-2451545.5-7/24)/36525; r=PI/180
    m=357.52910+35999.05030*t-0.0001559*t*t-0.00000048*t*t*t
    l=280.46645+36000.76983*t+0.0003032*t*t
    delta=(1.914600-0.004817*t-0.000014*t*t)*math.sin(m*r)
    delta+=(0.019993-0.000101*t)*math.sin(2*m*r)+0.000290*math.sin(3*m*r)
    return math.floor(((l+delta)*r % (2*PI))/PI*6)

def month_eleven(year):
    k=math.floor((julian(date(year,12,31))-2415021)/29.530588853)
    nm=new_moon(k)
    return new_moon(k-1) if sun_sector(nm)>=9 else nm

def leap_offset(a11):
    k=math.floor((a11-2415021.076998695)/29.530588853+0.5)
    previous=-1
    for i in range(1,15):
        current=sun_sector(new_moon(k+i))
        if current==previous:return i-1
        previous=current
    raise ValueError('Không xác định được tháng nhuận')

def solar_to_lunar(value):
    d=date.fromisoformat(value) if isinstance(value,str) else value
    if not 1900<=d.year<=2099:raise ValueError('Hỗ trợ ngày dương lịch từ năm 1900 đến 2099')
    day=julian(d);k=math.floor((day-2415021.076998695)/29.530588853)
    start=new_moon(k+1)
    if start>day:start=new_moon(k)
    a11=month_eleven(d.year);b11=a11
    if a11>=start:
        year=d.year;a11=month_eleven(d.year-1)
    else:
        year=d.year+1;b11=month_eleven(d.year+1)
    lunar_day=day-start+1;diff=math.floor((start-a11)/29);month=diff+11;leap=False
    if b11-a11>365:
        offset=leap_offset(a11)
        if diff>=offset:month=diff+10;leap=diff==offset
    if month>12:month-=12
    if month>=11 and diff<4:year-=1
    stems=['Giáp','Ất','Bính','Đinh','Mậu','Kỷ','Canh','Tân','Nhâm','Quý']
    branches=['Tý','Sửu','Dần','Mão','Thìn','Tỵ','Ngọ','Mùi','Thân','Dậu','Tuất','Hợi']
    return {'solar_date':d.isoformat(),'day':lunar_day,'month':month,'year':year,'leap_month':leap,
        'year_name':stems[(year+6)%10]+' '+branches[(year+8)%12],'timezone':'Asia/Ho_Chi_Minh'}
