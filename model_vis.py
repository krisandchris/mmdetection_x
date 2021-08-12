from torch import models as model
from torchsummary import summary

PATH='/home/tione/notebook/x/mmdetection/checkpoints/vfnet_r50_fpn_mdconv_c3-c5_mstrain_2x_coco_20201027pth-6879c318.pth'
# model_dict=torch.load(PATH)
model_dict=model.load_state_dict(torch.load(PATH))
# summary(model, (3, 1333, 800))
print(model_dict)