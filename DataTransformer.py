import linecache
import pickle
import json
import numpy as np

#统计测试文件图片行数
fn = 'test_sorted_num.txt'
line_count=0
for l in open(fn,'r',encoding='utf-8'):
            line_count += 1
image_order=[]

#记录每个图片文件按照提交顺序记录应该存放的位置，例：第一个文件编号10933的数组下标为932位
for line_i in range(1,line_count+1):#得到第line_i个文件的全部路径信息         
    line = linecache.getline(fn, line_i)#
    a = int(line) - 10001
    image_order.append(a)

#根据数组记录的下标完成排序
F=open('results/vfnetX_R2_swa.pkl','rb')
content=pickle.load(F)
ans = [0] * 3000#生成3000个测试文件空位
for i in range (0,3000):
    ans[image_order[i]]=content[i]#按照统计的下标填入数据
result=[]#最终输出
#遍历每个图像
for image in ans:
    #遍历每个类别
    image_list=[]#一张图片的结果
    for class_i in image:
        #遍历类别的数量
        class_i_list=[]#每张图片中每个类别的结果
        for num_i in class_i:
            num_i_list=[]#每张图片中每个类别包含的检测结果
            for num in num_i:
                num_i_list.append(format(num,'.3f'))#转换各个数据
            class_i_list.append(num_i_list)
        image_list.append(class_i_list)
    result.append(image_list)
with open('vfnetX_R2_swa.json', 'w', encoding='UTF-8') as fp:
   fp.write(json.dumps(result, indent=2, ensure_ascii=False))
print("成功写入文件。")
