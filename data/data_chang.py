input_path = "v3.0train.txt"
output_path = "train.txt"

b = ["儿科","耳鼻咽喉科","风湿免疫科","妇产科","感染科 传染科","骨科","呼吸内科","乳腺外科","精神心理科","口腔科","泌尿外科","内分泌科","皮肤科","普通内科","普外科","神经内科","神经外科","疼痛科 麻醉科","消化内科","心血管内科","性病科","血液科","眼科","疫苗科","影像检验科","肿瘤科","肛肠外科","中医科","胸外科","烧伤科","整形科","肝胆外科","急诊科","头颈外科"]
c = 0

with open(output_path,"w",encoding="UTF-8") as out:
    with open(input_path,encoding="UTF-8") as input:
        for i in input:

            a = i.split()
            if a[0]=="疼痛科":
                a.remove("麻醉科")
                a[0]="疼痛科 麻醉科"
            elif a[0]=="感染科":
                a.remove("传染科")
                a[0]="感染科 传染科"
            m_k = 1
            m = ""
            for d in a:
                if d in b:
                    a.remove(d)
                    if m_k == 1:
                        m = d
                        m_k -= 1
            f_o = ""
            k = len(a)
            for j in a:
                f_o = f_o + j
                if k > 1:
                    f_o = f_o + " "
                k -= 1
            f_o = f_o + "	"
            
            
            f_o = f_o + str(b.index(m))
            out.write(f_o+"\n")
    