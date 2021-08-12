import json
str_file = 'vfnet_swa_R2.bbox.json'
with open(str_file, 'r') as f:
    print("Load str file from {}".format(str_file))
    str1 = f.read()
r = json.loads(str1)
result = []
for i in range(0,3000):
    result.append([])
for a in result:
    a.append([])
    a.append([])
    a.append([])
    a.append([])
    a.append([])
    a.append([])
    a.append([])
    a.append([])
    a.append([])
    a.append([])
    a.append([])
    a.append([])
for zd in r:
    zd['bbox'].append(zd['score'])
    result[int(zd['image_id'])+10000][int(zd['category_id'])].append(zd['bbox'])
with open('yololast1.json', 'w', encoding='UTF-8') as fp:
   fp.write(json.dumps(result, indent=2, ensure_ascii=False))
print("成功写入文件。")