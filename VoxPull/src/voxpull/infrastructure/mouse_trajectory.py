"""独立鼠标轨迹生成算法（仅依赖 Python 标准库）。

生成：python3 鼠标轨迹算法.py --distance 160 --seed 2026
不传 --seed 时每次随机，输出会记录实际种子；同种子同参数可复现。
输出位置轨迹、水平进度、速度曲线；速度由位置函数求导获得。
"""
import argparse
import json
import math
from pathlib import Path
import random

VERSION='分阶段连续运动-v3-首峰增强'
NAMES={'T':'总用时（毫秒）','a':'起步等待占比','fast':'快移时段占剩余时间比例','fine':'微调时段占剩余时间比例','w':'快移完成位移比例','drift':'纵向漂移系数','A':'弧线系数','B':'起伏系数'}

PARAMETERS = json.loads(r'''
{
  "算法版本": "分阶段连续运动-v3-首峰增强",
  "样本数": 14,
  "参数分布": {
    "总用时（毫秒）": {
      "下限": 1195.82,
      "上限": 1937.0500000000002,
      "中心": 1533.607142857143
    },
    "起步等待占比": {
      "下限": 0.05,
      "上限": 0.14250000000000004,
      "中心": 0.09464285714285715
    },
    "快移时段占剩余时间比例": {
      "下限": 0.1956140350877193,
      "上限": 0.6415126050420169,
      "中心": 0.43338413170345946
    },
    "微调时段占剩余时间比例": {
      "下限": 0.1341614906832298,
      "上限": 1.0,
      "中心": 0.45692124407994006
    },
    "快移完成位移比例": {
      "下限": 0.8308821632117103,
      "上限": 0.9880939612574482,
      "中心": 0.9251560181962486
    },
    "纵向漂移系数": {
      "下限": -0.11204892640584768,
      "上限": 0.02936529356161799,
      "中心": -0.03317833291078091
    },
    "弧线系数": {
      "下限": -0.010052012048903141,
      "上限": 0.02892361630159382,
      "中心": 0.008515747651496559
    },
    "起伏系数": {
      "下限": -0.007450091519526214,
      "上限": 0.0033869122688956854,
      "中心": -0.001169862414210307
    }
  },
  "首峰形状": {
    "下限": 1.4,
    "上限": 1.9,
    "中心": 1.65,
    "说明": "独立形状参数；数值越大，第一峰越集中、越高，位移积分保持不变。"
  }
}
''')

def pulse(z,fast,sharpness=1.):
    if z<=0:return 0.,0.
    if z>=1:return 1.,0.
    if fast:
        # Compress time around the original peak (z=1/4), preserving area.
        # The warp and its first derivative are continuous at the peak.
        peak=.25
        if z<=peak:
            r=z/peak;warped=peak*r**sharpness;rate=sharpness*r**(sharpness-1)
        else:
            r=(1-z)/(1-peak);warped=1-(1-peak)*r**sharpness;rate=sharpness*r**(sharpness-1)
        return 10*warped**2-20*warped**3+15*warped**4-4*warped**5,20*warped*(1-warped)**3*rate
    return 3*z*z-2*z**3,6*z*(1-z)

def motion(u,p):
    a,b,e,w=p['a'],p['b'],p['e'],p['w']
    f,df=pulse((u-a)/(b-a),True,p.get('sharp',1.))
    s,ds=pulse((u-b)/(e-b),False)
    return w*f+(1-w)*s,w*df/(b-a)+(1-w)*ds/(e-b)

def sample_parameters(model,rng):
    def draw(key):
        s=model['参数分布'][NAMES[key]];low,high=s['下限'],s['上限']
        return low if high-low<1e-12 else rng.triangular(low,high,max(low,min(high,s['中心'])))
    a=draw('a');b=a+(1-a)*draw('fast');e=b+(1-b)*draw('fine')
    parameters={'T':draw('T'),'a':a,'b':b,'e':e,'w':draw('w'),**{k:draw(k) for k in ('drift','A','B')}}
    shape=model.get('首峰形状',{'下限':1.4,'上限':1.9,'中心':1.65})
    low,high,center=[shape[k] for k in ('下限','上限','中心')]
    if not 1<=low<=center<=high<=3:raise ValueError('首峰锐度范围应在 1 至 3 之间')
    parameters['sharp']=low if low==high else rng.triangular(low,high,center)
    return parameters

def generate(model,distance,start=(0,0),seed=None,duration_ms=None,end_dy=None,step_ms=16):
    if not math.isfinite(distance) or distance==0:raise ValueError('距离必须为非零有限数值')
    if len(start)!=2 or not all(math.isfinite(v) for v in start):raise ValueError('起点无效')
    if not math.isfinite(step_ms) or step_ms<=0:raise ValueError('采样间隔必须为正数')
    if end_dy is not None and not math.isfinite(end_dy):raise ValueError('纵向位移无效')
    if seed is None:seed=random.SystemRandom().randrange(2**63)
    p=sample_parameters(model,random.Random(seed))
    if duration_ms is not None:p['T']=duration_ms
    T=p['T']
    if not math.isfinite(T) or T<=0:raise ValueError('用时必须为正数')
    if end_dy is not None:p['drift']=end_dy/abs(distance)
    timestamps=sorted({0.,T,*[i*step_ms for i in range(1,math.ceil(T/step_ms))],*[p[k]*T for k in ('a','b','e')]})
    xy=[];speed=[];progress=[]
    for t in timestamps:
        q,dq=motion(t/T,p);dy=p['drift']*q+p['A']*math.sin(math.pi*q)+p['B']*math.sin(2*math.pi*q)
        dydq=p['drift']+math.pi*p['A']*math.cos(math.pi*q)+2*math.pi*p['B']*math.cos(2*math.pi*q)
        xy.append({'时间（毫秒）':t,'鼠标横坐标（像素）':start[0]+distance*q,'鼠标纵坐标（像素）':start[1]+abs(distance)*dy})
        speed.append({'时间（毫秒）':t,'速度（像素每秒）':math.hypot(distance,abs(distance)*dydq)*dq*1000/T})
        progress.append({'时间（毫秒）':t,'水平进度':q})
    return {'算法版本':VERSION,'随机种子':seed,'来源样本数':model['样本数'],'阶段参数':{NAMES['T']:T,'起步结束比例':p['a'],'快移结束比例':p['b'],'微调结束比例':p['e'],**{NAMES[k]:p[k] for k in ('w','drift','A','B')}},'起点':list(start),
            '首峰锐度':p['sharp'],'水平位移（像素）':distance,'总用时（毫秒）':T,'校验状态':'未执行',
            '鼠标位置轨迹':xy,'水平进度随时间变化':progress,'速度曲线':speed}


def generate_trajectory(distance, start=(0, 0), seed=None, total_ms=None,
                        end_dy=None, interval_ms=16):
    """距离/坐标为浏览器 CSS 像素，时间为毫秒。

    end_dy=0：终点与起点等高；省略则随机保留小幅纵向漂移。
    结果是运动计划，不表示网页已执行或验证通过。
    """
    return generate(PARAMETERS, distance, start, seed, total_ms, end_dy, interval_ms)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distance',type=float,required=True)
    parser.add_argument('--start-x',type=float,default=0)
    parser.add_argument('--start-y',type=float,default=0)
    parser.add_argument('--seed',type=int)
    parser.add_argument('--total-ms',type=float)
    parser.add_argument('--end-dy',type=float)
    parser.add_argument('--out',default='生成轨迹.json')
    args=parser.parse_args()
    plan=generate_trajectory(args.distance,(args.start_x,args.start_y),args.seed,args.total_ms,args.end_dy)
    output=Path(args.out)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print('已生成：'+str(output.resolve()))
