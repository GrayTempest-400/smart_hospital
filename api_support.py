from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import torch
from pytorch_pretrained import BertModel, BertTokenizer
import torch.nn as nn
from pydantic import BaseModel

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Config(object):
    """Configuration for model parameters."""

    def __init__(self, dataset):
        self.class_list = [x.strip() for x in open(dataset + '/data/class.txt', encoding="UTF-8").readlines()]
        self.save_path = 'Data/saved_dict/bert.ckpt'
        self.device = torch.device('cpu')
        self.num_classes = len(self.class_list)
        self.batch_size = 128
        self.pad_size = 32
        self.learning_rate = 5e-5
        self.bert_path = './bert_pretrain'
        self.tokenizer = BertTokenizer.from_pretrained(self.bert_path)
        self.hidden_size = 768

    def build_dataset(self, text):
        lin = text.strip()
        pad_size = len(lin)
        token = self.tokenizer.tokenize(lin)
        token = ['[CLS]'] + token
        token_ids = self.tokenizer.convert_tokens_to_ids(token)
        token_ids = token_ids[:pad_size]
        mask = [1] * pad_size
        return torch.tensor([token_ids], dtype=torch.long), torch.tensor([mask])


class Model(nn.Module):
    def __init__(self, config):
        super(Model, self).__init__()
        self.bert = BertModel.from_pretrained(config.bert_path)
        for param in self.bert.parameters():
            param.requires_grad = True
        self.fc = nn.Linear(config.hidden_size, config.num_classes)

    def forward(self, x):
        context = x[0]
        mask = x[1]
        _, pooled = self.bert(context, attention_mask=mask, output_all_encoded_layers=False)
        out = self.fc(pooled)
        return out


# Load the model and config
dataset = 'Data'  # Dataset path
config = Config(dataset)
model = Model(config).to(config.device)
model.load_state_dict(torch.load(config.save_path, map_location='cpu'))
torch.cuda.manual_seed_all(1)
torch.backends.cudnn.deterministic = True  # 保证每次结果一样

key = {
    0: "儿科", 1: "耳鼻咽喉科", 2: "风湿免疫科", 3: "妇产科", 4: "感染科 传染科", 5: "骨科", 6: "呼吸内科",
    7: "乳腺外科", 8: "精神心理科", 9: "口腔科", 10: "泌尿外科", 11: "内分泌科", 12: "皮肤科",
    13: "普通内科", 14: "普外科", 15: "神经内科", 16: "神经外科", 17: "疼痛科 麻醉科", 18: "消化内科",
    19: "心血管内科", 20: "性病科", 21: "血液科", 22: "眼科", 23: "疫苗科", 24: "影像检验科",
    25: "肿瘤科", 26: "肛肠外科", 27: "中医科", 28: "胸外科", 29: "烧伤科", 30: "整形科",
    31: "肝胆外科", 32: "急诊科", 33: "头颈外科"
}

class TextRequest(BaseModel):
    text: str

@app.post("/predict")
async def predict(request: TextRequest):
    data = config.build_dataset(request.text)
    with torch.no_grad():
        outputs = model(data)
        num = torch.argmax(outputs)
    department = key[int(num)]
    return {"department": department}

@app.get("/")
async def root():
    return {"message": "Medical Department Classification API"}
#uvicorn api_support:app --reload