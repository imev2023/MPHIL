# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 10:00 2023

@author: listonlab
"""

from Data import Data,Log_transformer,Standard_tranformer
import pickle as pk
import os
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score,roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, balanced_accuracy_score,roc_auc_score
from sklearn.linear_model import LogisticRegression
from joblib import Parallel, delayed
import torch
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
import itertools
from sklearn import metrics
#generate data ST1
seed = 1235711
fold = os.getcwd()
fold

### generate data

data = Data()

### load and contruct dataset ###
file = open(fold +"/data/ST1/dataset_cell_cnn_batch_noaug.dat","rb")
train_data, val_data  = pk.load(file)
file.close()
#train_loader = DataLoader(dataset=train_data, batch_size=64, shuffle=True)
#val_loader = DataLoader(dataset=val_data, batch_size=64, shuffle=False)

# Input shape is determined by the number of cells sampled from each sample and the number of markers (30 = ST2)
imput_shape = train_data.__getitem__(0)[0].size()
imput_size = 1
for v in imput_shape:
    imput_size*=v



### defining model ###
class Model_CVRobust(torch.nn.Module):
    def __init__(self,imput_size, num_markers):
        super().__init__()
        torch.set_default_dtype(torch.float64)
        self.flatten = torch.flatten
        self.cov1 = torch.nn.Conv2d(in_channels=1, out_channels=3, kernel_size=(1,num_markers))
        self.cov2 = torch.nn.Conv2d(in_channels=3, out_channels=3, kernel_size=(1,1))
        self.fc1 = torch.nn.Linear(in_features=3, out_features=1)
        self.avPoll=torch.nn.AvgPool2d(kernel_size=(10000,1),stride =1)
        self.sigmoid = torch.nn.Sigmoid()
        self.relu = torch.nn.ReLU()
        # self.do = torch.nn.Dropout1d(p=0.2)
        # self.bn = torch.nn.BatchNorm1d(1000)
        self.optimizer=None
    def forward(self, x):
        #print(x.shape)
        x = self.relu(self.cov1(x))
        # x = self.bn(x)
        #print(x.shape)
        x = self.relu(self.cov2(x))
        # print(x.shape)
        # x = self.bn(x)
        #print(x.shape)
        x = self.avPoll(x)
        x = self.flatten(x,start_dim=1)
        #print(x.shape)
        x = self.fc1(x)
        x = self.sigmoid(x)
        return x
    
class Model_CVRobust_Dense(torch.nn.Module):
    def __init__(self,imput_size, num_markers):
        super().__init__()
        torch.set_default_dtype(torch.float64)
        self.flatten = torch.flatten
        self.cov1 = torch.nn.Conv2d(in_channels=1, out_channels=5, kernel_size=(1,num_markers))
        self.cov2 = torch.nn.Conv2d(in_channels=5, out_channels=1, kernel_size=(1,1))
        # self.fc1 = torch.nn.Linear(in_features=1, out_features=1)
        self.avPoll=torch.nn.AvgPool2d(kernel_size=(1000,1),stride =1)
        self.sigmoid = torch.nn.Sigmoid()
        self.relu = torch.nn.ReLU()
        self.fc1 = torch.nn.Linear(in_features=1, out_features=8)
        self.fc2 = torch.nn.Linear(in_features=8, out_features=4)
        self.fc3 = torch.nn.Linear(in_features=4, out_features=1)
        # self.do = torch.nn.Dropout1d(p=0.2)
        # self.bn = torch.nn.BatchNorm1d(1000)
        self.optimizer=None
    def forward(self, x):
        x = self.relu(self.cov1(x))
        # x = self.bn(x)
        # print(x.shape)
        x = self.relu(self.cov2(x))
        # print(x.shape)
        # x = self.bn(x)
        # print(x.shape)
        x = self.avPoll(x)
        # print(x.shape)
        # x = self.flatten(x)
        # # print(x.shape)
        x = self.relu(self.fc1(x))
        # print(x.shape)
        x = self.relu(self.fc2(x))
        x = self.relu(self.fc3(x))
        # print(x.shape)
        x = self.sigmoid(x)
        return x
    

class Model_Linear(torch.nn.Module):
    def __init__(self,imput_size, num_markers):
        super().__init__()
        torch.set_default_dtype(torch.float64)
        self.flatten = torch.flatten
        self.cov1 = torch.nn.Conv2d(in_channels=1, out_channels=5, kernel_size=(1,num_markers))
        self.fc1 = torch.nn.Linear(in_features=5, out_features=1)
        self.sigmoid = torch.nn.Sigmoid()
        self.relu = torch.nn.ReLU()
        self.avPoll=torch.nn.AvgPool2d(kernel_size=(1000, 1),stride =1)
        # self.do = torch.nn.Dropout1d(p=0.2)
        self.optimizer=None
    def forward(self, x):
        x = self.relu(self.cov1(x))
        x = self.avPoll(x)
        x = self.flatten(x)
        x = self.sigmoid(self.fc1(x))
        return x
    
class Model_CV2(torch.nn.Module):
    def __init__(self,imput_size, num_markers):
        super().__init__()
        self.flatten = torch.flatten
        self.fc1 = torch.nn.Linear(in_features=3, out_features=1)
        self.cov1 = torch.nn.Conv2d(in_channels=1, out_channels=3, kernel_size=(1,num_markers))
        self.cov2 = torch.nn.Conv2d(in_channels=3, out_channels=3, kernel_size=(1,1))
        self.maxPoll=torch.nn.MaxPool2d(kernel_size=(1000,1),stride =1)
        self.sigmoid = torch.nn.Sigmoid()
        self.relu = torch.nn.ReLU()
        self.optimizer=None
    def forward(self, x):
        x = self.relu(self.cov1(x))
        x = self.relu(self.cov2(x))
        x = self.maxPoll(x)
        x = self.flatten(x)
        x = self.sigmoid(self.fc1(x))
        return x
    
### construct Neural_network ### 

class Neural:
    def __init__(self,train_dataset,val_dataset,model,optimizer,loss_f, device,sumary_lab=False,bach_size=16):
        self.train_loader = DataLoader(dataset=train_data, batch_size=bach_size, shuffle=True)
        self.bach_size = bach_size
        self.val_loader = DataLoader(dataset=val_data, batch_size=bach_size, shuffle=False)
        self.model = model
        self.optimizer = optimizer
        self.loss_f = loss_f
        self.device = device
        self.sumary_lab = sumary_lab
        self.model.to(device)
        if(sumary_lab!=False):
            self.writer= SummaryWriter(fold+"/runs/"+self.sumary_lab)
        else:
            self.writer=None
        
    def trainning(self,num_epochs,file_out,test_dataset=None):
        for epoch in range(num_epochs):
            ###TRAINING###
            tloss,b_acuracy,si = 0, 0, 0
            
            for batch_x,batch_y in self.train_loader:
                self.model.train()
                si+=1
                batch_x.to(self.device)
                batch_y.to(self.device)
                y_pred = self.model(batch_x) 
                
                ### Add loss ###
                loss = self.loss_f(y_pred, batch_y.unsqueeze(1))
                loss.backward()
                self.optimizer.step()
                self.optimizer.zero_grad()
                tloss+=loss.detach().item()
                y_pred = y_pred.detach().tolist()
                batch_y = batch_y.detach().tolist()
                y_pred = [a[0] for a in y_pred]
                fpr, tpr, thresholds = metrics.roc_curve(batch_y,y_pred, pos_label=1)
                b_acuracy+=metrics.auc(fpr, tpr)
                    
            ### Average validation loss and score for all batches ###
            # print(si)
            tloss = tloss/si
            b_acuracy = b_acuracy/si
            # sfscore = sfscore/si
            # sscore = sscore/si
            print("------------------")
            print("training loss: ", str(tloss), "training accuracy: "+str(b_acuracy)) #, " fscore: ", str(sfscore))
            # print("------------------")

            ###VALIDATION###
            self.model.eval()
            ### Add accuracy ###
            vloss,vb_acuracy,si = 0, 0, 0
            with torch.no_grad():
                for batch_x,batch_y in self.val_loader:
                    si+=1
                    batch_x.to(self.device)
                    batch_y.to(self.device)
                    y_pred = self.model(batch_x)
                    loss = self.loss_f(y_pred, batch_y.unsqueeze(1))
                    vloss+=loss.detach().item()
                    y_pred = y_pred.detach().tolist()
                    batch_y = batch_y.detach().tolist()
                    y_pred = [a[0] for a in y_pred]
                    fpr, tpr, thresholds = metrics.roc_curve(batch_y,y_pred, pos_label=1)
                    vb_acuracy+=metrics.auc(fpr, tpr)
                        
                ### Average validation loss and score for all batches ###
                # print(si)
                vloss = vloss/si
                vb_acuracy = vb_acuracy/si
                    # print("------------------")
                print("val loss: ", str(vloss), "val accuracy: "+str(vb_acuracy)) #, " fscore: ", str(sfscore))
                print("------------------")
                if(epoch%20==0):
                    self._save(fold+"/data/ST1/ST1_models/"+self.sumary_lab +".dat", epoch, num_epochs)
                print(epoch)
            if(self.sumary_lab!=False):
                self.writer.add_scalars(main_tag=self.sumary_lab, 
                                        tag_scalar_dict={"Loss/train":tloss,
                                                         "Loss/validation":vloss, 
                                                         "B_Accuracy/train":b_acuracy, 
                                                         "b_Accuracy/validation":vb_acuracy},
                                        global_step=epoch)
        self.save_res(file_out,test_dataset)
        if(self.sumary_lab!=False):
            self._writer_close()
        
    def _save(self,file,epoch,num_epochs):
        mod = {"model":self.model.state_dict(),"epoch":epoch,"opt":self.optimizer.state_dict(),"train_loader":self.train_loader,
                "val_loader":self.val_loader,"num_epochs":num_epochs,"loss_f":self.loss_f,"sumary_lab":self.sumary_lab,
                "device":self.device}
        torch.save(mod, file)
        
    def _writer_close(self):
        self.writer.close()
        
    def save_res(self,file,test_dataset=None):
        self.model.eval()
        with torch.no_grad():
            ytrain_true=[]
            ytrain_pred=[]
            for bx,by in self.train_loader:
                bx.to(self.device)
                ytrain_true.append(by) 
                ytrain_pred.append(self.model(bx))
            yval_true=[]
            yval_pred=[]
            for bx,by in self.val_loader:
                bx.to(self.device)
                yval_true.append(by) 
                yval_pred.append(self.model(bx))
            if(test_dataset!=None):
                tes_loader = DataLoader(dataset=test_dataset, batch_size=16, shuffle=False)
                ytest_true=[]
                ytest_pred=[]
                for bx,by in tes_loader:
                    bx.to(self.device)
                    ytest_true.append(by) 
                    ytest_pred.append(self.model(bx))
                ytrain_true=[]
                ytrain_pred=[]
                
                mod = {"model":self.model.state_dict(),"train_loader":self.train_loader,
                        "val_loader":self.val_loader,"test_loader":tes_loader,"sumary_lab":self.sumary_lab,
                        "ytrain_true":ytrain_true,"ytrain_pred":ytrain_pred, 
                        "yval_true":yval_true,"yval_pred":yval_pred, 
                        "ytest_true":ytest_true,"ytest_pred":ytest_pred}
            
            else:
                mod = {"model":self.model.state_dict(),"train_loader":self.train_loader,
                        "val_loader":self.val_loader,"sumary_lab":self.sumary_lab,
                        "ytrain_true":ytrain_true,"ytrain_pred":ytrain_pred, 
                        "yval_true":yval_true,"yval_pred":yval_pred}
            file = open(file,"wb")
            pk.dump(mod, file)
            file.close()

# #####################################################################################################

### Define the hyperparameter values to explore ###
batch_size=100
lr = 0.001

device = "cpu"
torch.set_num_threads(16)
loss_f = torch.nn.BCELoss()


# model = Model_CVRobust(imput_size, num_markers=30)
# optimizer=torch.optim.Adam(model.parameters(), lr=lr)
# net = Neural(train_data,val_data,model=model, loss_f=loss_f,optimizer=optimizer,device=device,sumary_lab="modelCVRobust_bs16_do02lr05",bach_size=batch_size)                  
# net.trainning(num_epochs=100, file_out=fold+"/ST2/scoresModelCVRobust_do02lr05", test_dataset=None)  


# # model = Model_Linear(imput_size, num_markers=30)
# # optimizer=torch.optim.Adam(model.parameters(), lr=lr)
# # # optimizer = torch.optim.Adam(model.parameters(), lr=lr)
# # net = Neural(train_data,val_data,model=model, loss_f=loss_f,optimizer=optimizer,device=device,sumary_lab="modelLinear_bs16",bach_size=batch_size)                  
# # net.trainning(num_epochs=500, test_dataset=None, file_out=fold+"/ST2/cellCnn/scoresmodelLinear")               
       
# model = Model_CVRobust_Dense(imput_size, num_markers=30)
# optimizer=torch.optim.Adam(model.parameters(), lr=lr)
# net = Neural(train_data,val_data,model=model, loss_f=loss_f,optimizer=optimizer,device=device,sumary_lab="modelCV_dense10_do02lr05",bach_size=batch_size)                  
# net.trainning(num_epochs=100, file_out=fold+"/ST2/scoresModelCV_dense10_do02lr05", test_dataset=None)  

# model = Model_CV2(imput_size, num_markers=28)
# optimizer=torch.optim.Adam(model.parameters(), lr=lr)
# net = Neural(train_data,val_data,model=model, loss_f=loss_f,optimizer=optimizer,device=device,sumary_lab="modelCV2_1307_9_45s",bach_size=batch_size)                  
# net.trainning(num_epochs=1, file_out=fold+"/Results/ST1/CV2/1307_8_38", test_dataset=None)  


model = Model_CVRobust(imput_size, num_markers=28)
optimizer=torch.optim.Adam(model.parameters(), lr=lr)
net = Neural(train_data,val_data,model=model, loss_f=loss_f,optimizer=optimizer,device=device,sumary_lab="modelCVRobust_19_07_1600",bach_size=batch_size)                  
net.trainning(num_epochs=2000, file_out=fold+"/data/Results/ST1/CVRobust_19_07_1600.dat", test_dataset=None)  

# model = Model_Linear(imput_size, num_markers=28)
# optimizer=torch.optim.Adam(model.parameters(), lr=lr)
# net = Neural(train_data,val_data,model=model, loss_f=loss_f,optimizer=optimizer,device=device,sumary_lab="modelLinear_1307_8_5channels",bach_size=batch_size)                  
# net.trainning(num_epochs=1, test_dataset=None, file_out=fold+"/Results/ST1/Linear/Linear_1206_18_10")               
       
# model = Model_CVRobust_Dense(imput_size, num_markers=28)
# optimizer=torch.optim.Adam(model.parameters(), lr=lr)
# net = Neural(train_data,val_data,model=model, loss_f=loss_f,optimizer=optimizer,device=device,sumary_lab="modelCV_dense_1307_8_5channels",bach_size=batch_size)                  
# net.trainning(num_epochs=1, file_out=fold+"/Results/ST1/Dense/Dense_1307_8_38", test_dataset=None)  






# # ### definning model
# # class Model_CVRobust(torch.nn.Module):
# #     def __init__(self,imput_size):
# #         super().__init__()
# #         torch.set_default_dtype(torch.float64)
# #         self.flatten = torch.flatten
# #         self.cov1 = torch.nn.Conv2d(in_channels=1, out_channels=3, kernel_size=(1,28))
# #         self.cov2 = torch.nn.Conv2d(in_channels=3, out_channels=1, kernel_size=(1,1))
# #         # self.fc1 = torch.nn.Linear(in_features=1, out_features=1)
# #         self.avPoll=torch.nn.AvgPool2d(kernel_size=(1000,1),stride =1)
# #         self.sigmoid = torch.nn.Sigmoid()
# #         self.relu = torch.nn.ReLU()
# #         self.do = torch.nn.Dropout1d(p=0.1)
# #         self.optimizer=None
# #     def forward(self, x):
# #         x = self.do(self.relu(self.cov1(x)))
# #         x = self.do(self.relu(self.cov2(x)))
# #         x = self.avPoll(x)
# #         x = self.flatten(x)
# #         x = self.sigmoid(x)
# #         return x
    
# # class Model_CV1(torch.nn.Module):
# #     def __init__(self,imput_size):
# #         super().__init__()
# #         torch.set_default_dtype(torch.float64)
# #         self.flatten = torch.flatten
# #         self.fc1 = torch.nn.Linear(in_features=imput_size, out_features=1)
# #         self.sigmoid = torch.nn.Sigmoid()
# #         self.relu = torch.nn.ReLU()
# #         self.do = torch.nn.Dropout1d(p=0.1)
# #         self.optimizer=None
# #     def forward(self, x):
# #         x = self.do(self.relu(self.cov1(x)))
# #         x = self.maxPoll(x)
# #         x = self.flatten(x)
# #         x = self.sigmoid(self.fc1(x))
# #         return x
    

    

