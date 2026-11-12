import csv,json,math
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix,precision_score,recall_score
from .common import ROOT,save_json

def evaluate():
    train_rng=np.random.default_rng(552505);test_rng=np.random.default_rng(552506)
    mean=[5,60,75];std=[.7,8,6]
    train=train_rng.normal(mean,std,(1200,3));normal=test_rng.normal(mean,std,(300,3))
    abnormal=np.vstack([test_rng.normal([13,60,75],[1,8,6],(20,3)),
        test_rng.normal([5,8,75],[.7,3,6],(20,3)),test_rng.normal([5,60,10],[.7,8,3],(20,3))])
    x=np.vstack([normal,abnormal]);y=np.r_[np.zeros(300,dtype=int),np.ones(60,dtype=int)]
    model=IsolationForest(n_estimators=150,contamination=.03,random_state=552505,n_jobs=1)
    model.fit(train);pred=(model.predict(x)==-1).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    result=dict(algorithm='IsolationForest',training_normal=1200,test_normal=300,test_anomaly=60,
        seeds=[552505,552506],features=['temperatura_C','nivel_percent','energia_percent'],
        threshold='contamination=0.03 definido antes do conjunto de teste',
        precision=float(precision_score(y,pred,zero_division=0)),recall=float(recall_score(y,pred,zero_division=0)),
        false_positive_rate=float(fp/(fp+tn)),true_negative=int(tn),false_positive=int(fp),false_negative=int(fn),true_positive=int(tp),
        limitation='Dados sintéticos independentes. Não demonstram desempenho em campo nem resistência a adversários.',
        actuation=False,llm=False)
    folder=ROOT/'data';folder.mkdir(exist_ok=True)
    for name,data,labels in [('train.csv',train,np.zeros(len(train),int)),('test.csv',x,y)]:
        with (folder/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(result['features']+['anomaly'])
            for row,label in zip(data,labels):w.writerow([round(float(v),4) for v in row]+[int(label)])
    save_json(ROOT/'evidence/ai.json',result);return result

if __name__=='__main__':print(json.dumps(evaluate()))
