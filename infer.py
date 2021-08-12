import mmcv
import os
import numpy as np
from mmcv.runner import load_checkpoint
from mmdet.models import build_detector
from mmdet.apis import init_detector, inference_detector


config_file = 'work_dirs/vf_R2101-41.py'
#checkpoint_file = 'work_dirs/2_vf_R2101/latest.pth'
checkpoint_file = 'work_dirs/swa_model/swa_1-12.pth'

model = init_detector(config_file,checkpoint_file, device='cuda:0')

img_dir = 'data/'
out_dir = 'results/'

if not os.path.exists(out_dir):
    os.mkdir(out_dir)


fp = open('data/test_sorted.txt','r')
test_list = fp.readlines()

imgs=[]
for test_1 in test_list:
    test_1 = test_1.replace('\n','')
    name = img_dir + test_1
    imgs.append(name)

results = []
# for i,result in enumerate(inference_detector(model,imgs)):
#     print('model is processing the {}/{} images.'.format(i+1,len(imgs)))
#     results.append(result)

count = 0
for img in imgs:
    count += 1
    print('model is processing the {}/{} images.'.format(count,len(imgs)))
    result = inference_detector(model,img)
    results.append(result)

print('\nwriting results to {}'.format('vfnetX_R2_swa.pkl'))
mmcv.dump(results,out_dir+'vfnetX_R2_swa.pkl')