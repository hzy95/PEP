#encoding:utf-8
import pandas as pd
import numpy as np
import os
import sys
import math
import random
import scipy
import scipy.io

from sklearn.ensemble import GradientBoostingClassifier

from sklearn import preprocessing
import sklearn.preprocessing
from sklearn.externals import joblib
from sklearn.metrics import average_precision_score,precision_score,recall_score,f1_score
from sklearn.metrics import roc_auc_score,accuracy_score,matthews_corrcoef
from sklearn import datasets

import processSeq
import warnings

from sklearn import cross_validation
from sklearn.cross_validation import cross_val_score,StratifiedKFold,cross_val_predict, KFold
from sklearn.metrics import roc_auc_score,accuracy_score,matthews_corrcoef,precision_recall_curve

import xgboost as xgb
from sklearn.decomposition import PCA
import random

def getData(type,cell):
	data = pd.read_table('./Data/Learning/supervised_'+str(cell)+"_"+str(type))
	data['predict'] = pd.Series(0,index = data.index)
	data['predict_proba'] = pd.Series(0,index = data.index)
	weight = float(len(data[data["label"] == 0]))/float(len(data[data["label"] == 1]))
	data['weight'] = (weight - 1)*data['label']+1
	
	print "Pos : %d Neg : %d" %(len(data[data["label"] == 1]),len(data[data["label"] == 0]))
	print max(data["weight"])
	return data

def analyzeResult_temp(data,model,DataVecs):
	predict = model.predict(DataVecs)
	data['predict'] = predict
	print ("Accuracy: %f %%" % (100. * sum(data["label"] == data["predict"]) / len(data["label"])))
	answer1 = data[data["label"] == 1]
	answer2 = data[data["label"] == 0]
	print ("Positive Accuracy: %f %%" % (100. * sum(answer1["label"] == answer1["predict"]) / len(answer1["label"])))
	print ("Negative Accuracy: %f %%" % (100. * sum(answer2["label"] == answer2["predict"]) / len(answer2["label"])))
	try:
		result_auc = model.predict_proba(DataVecs)
		print ("Roc:%f\nAUPR:%f\n" % (roc_auc_score(data["label"],result_auc[:,1]),
			average_precision_score(data["label"],result_auc[:,1])))
		print("Precision:%f\nRecall:%f\nF1score:%f\nMCC:%f\n" %(precision_score(data["label"],data["predict"]),
			recall_score(data["label"],data["predict"]),
			f1_score(data["label"],data["predict"]),
			matthews_corrcoef(data["label"],data["predict"])))
	except:
		print "ROC unavailable"

def analyzeResult(data,model,DataVecs,threshold):
	predict = model.predict_proba(DataVecs)[:,1]
	True,False=1,0
	data['predict'] = (predict > threshold)
	print ("Accuracy: %f %%" % (100. * sum(data["label"] == data["predict"]) / len(data["label"])))
	answer1 = data[data["label"] == 1]
	answer2 = data[data["label"] == 0]
	print ("Positive Accuracy: %f %%" % (100. * sum(answer1["label"] == answer1["predict"]) / len(answer1["label"])))
	print ("Negative Accuracy: %f %%" % (100. * sum(answer2["label"] == answer2["predict"]) / len(answer2["label"])))
	try:
		result_auc = model.predict_proba(DataVecs)
		print ("Roc:%f\nAUPR:%f\n" % (roc_auc_score(data["label"],result_auc[:,1]),
			average_precision_score(data["label"],result_auc[:,1])))
		print("Precision:%f\nRecall:%f\nF1score:%f\nMCC:%f\n" %(precision_score(data["label"],data["predict"]),
			recall_score(data["label"],data["predict"]),
			f1_score(data["label"],data["predict"]),
			matthews_corrcoef(data["label"],data["predict"])))
	except:
		print "ROC unavailable"

def score_func(estimator,X,Y):
	global accuracy,precision,recall,f1,mcc,auc,aupr,resultpredict,resultproba,resultlabel
	predict_proba = estimator.predict_proba(X)[:,1]
	True,False=1,0
	predict = (predict_proba > 0.50)
	resultlabel = np.hstack((resultlabel,Y))
	resultpredict = np.hstack((resultpredict,predict))
	resultproba = np.hstack((resultproba,predict_proba))
	precision+=precision_score(Y,predict)
	recall+=recall_score(Y,predict)
	f1+=f1_score(Y,predict)
	accuracy += accuracy_score(Y,predict)
	mcc += matthews_corrcoef(Y,predict)
	auc += roc_auc_score(Y,predict_proba)
	aupr += average_precision_score(Y,predict_proba)
	print "finish one"
	return matthews_corrcoef(Y,predict)

def score_function(y_test,yfit):
	precision = precision_score(y_test,yfit)
	recall = recall_score(y_test,yfit)
	f1 = f1_score(y_test,yfit)
	mcc = matthews_corrcoef(y_test,yfit)
	return precision, recall, f1, mcc

def balance_data(data,dataDataVecs):
	data.index = xrange(len(data))
	posdata = data[data["label"] == 1]
	negdata = data[data["label"] == 0]
	posdatavecs = dataDataVecs[posdata.index]
	negdatavecs = dataDataVecs[negdata.index]
	newnegindex = np.random.permutation(negdata.index)
	newnegindex = newnegindex[0:len(posdata)]
	negdata = negdata.reindex(newnegindex)
	negdatavecs = dataDataVecs[newnegindex]
	data = pd.concat([posdata,negdata])
	dataDataVecs = np.vstack((posdatavecs,negdatavecs))
	data.index = xrange(len(data))
	return data,dataDataVecs

def run(word, num_features,k,type,cell):

	warnings.filterwarnings("ignore")

	global accuracy,precision,recall,f1,mcc,auc,aupr,resultpredict,resultproba,resultlabel
	accuracy,precision,recall,f1,mcc,auc,aupr=0,0,0,0,0,0,0
	resultpredict = np.zeros((1),dtype = "int")
	resultlabel = np.zeros((1),dtype="int")
	resultproba = np.zeros((1),dtype = "float32")
	resultindex = np.zeros((1),dtype="int")
	
	word = int(word)
	num_features = int(num_features)
	k=int(k)

	# Read data
	data = getData(type,cell)

	print "Loading Datavecs"
	dataDataVecs = np.load("./Datavecs/datavecs_"+str(cell)+"_"+str(type)+".npy")
	dataDataVecs = sklearn.preprocessing.StandardScaler().fit_transform(dataDataVecs)


	estimator = xgb.XGBClassifier(max_depth=10,learning_rate=0.1, n_estimators=1000,nthread=50)

	cv = StratifiedKFold(y = data["label"], n_folds = 10, shuffle = True, random_state = 0)

	for train_index, test_index in cv:
		resultindex = np.hstack((resultindex,test_index))
	
	scores= cross_val_score(estimator, dataDataVecs, data["label"],\
							scoring = score_func, cv = cv,\
	 						n_jobs = 1,fit_params={'sample_weight': data["weight"]})
	
	print "precision = %r\trecall = %r\tf1 = %r\taccuracy = %r\t mcc = %r\t auc = %r\t aupr = %r\n" \
	%(precision/10,recall/10,f1/10,accuracy/10,mcc/10,auc/10,aupr/10)

	result = np.vstack((resultindex,resultlabel,resultpredict,resultproba))
	result = result.T
	result = result[1:len(result)]
	df = pd.DataFrame(result,columns=['index','label','predict','proba'])
	df = df.sort(columns='index')
	#table_name = "./Data/"+str(cell)+"/pairs_"+str(type)+".csv"
	#table = pd.read_table(table_name,sep=",")
	#table["proba"] = df["proba"]
	#table["predict"] = df["predict"]

	df.to_csv("./Result/"+str(cell)+str(type)+".csv",index = False)

def threshold_estimate(x,y):
	x_train, x_test, y_train, y_test = cross_validation.train_test_split(x, y, test_size=0.1, random_state=0)
	weight = float(len(y_train[y_train == 0]))/float(len(y_train[y_train == 1]))
	w1 = np.array([1]*y_train.shape[0])
	w1[y_train==1]=weight
	print("samples: %d %d %f" % (x_train.shape[0], x_test.shape[0], weight))
	estimator = xgb.XGBClassifier(max_depth=10, learning_rate=0.1, n_estimators=1000, nthread=50)
	estimator.fit(x_train, y_train, sample_weight=w1)
	y_scores = estimator.predict_proba(x_test)[:,1]
	precision, recall, thresholds = precision_recall_curve(y_test, y_scores)
	f1 = 2*precision[2:]*recall[2:]/(precision[2:]+recall[2:])
	m_idx = np.argmax(f1)
	m_thresh = thresholds[2+m_idx]
	print("%d %f %f" % (precision.shape[0], f1[m_idx], m_thresh))
	return m_thresh

def threshold_estimate_cv(x,y,k_fold):
	print "%d %d %d" % (y.shape[0], sum(y==1), sum(y==0))
	kf1 = StratifiedKFold(y, n_folds=k_fold, shuffle=True, random_state=0)
	#print type(x)
	#print type(y)
	threshold = np.zeros((k_fold),dtype="float32")
	cnt = 0
	for train_index, test_index in kf1:
		x_train, x_test = x[train_index], x[test_index]
		y_train, y_test = y[train_index], y[test_index]
		#print "%d %d %d %d" % (y_train.shape[0], sum(y_train==1), sum(y_train==0), k_fold)
		#print "%d %d %d %d" % (y_test.shape[0], sum(y_test==1), sum(y_test==0), k_fold)
		w1 = np.array([1]*y_train.shape[0])
		weight = float(len(y_train[y_train == 0]))/float(len(y_train[y_train == 1]))
		w1 = np.array([1]*y_train.shape[0])
		w1[y_train==1]=weight
		#print("samples: %d %d %d %f" % (x_train.shape[0], x_test.shape[0], x_train.shape[1], weight))
		estimator = xgb.XGBClassifier(max_depth=10, learning_rate=0.1, n_estimators=1000, nthread=50)
		estimator.fit(x_train, y_train, sample_weight=w1)
		y_scores = estimator.predict_proba(x_test)[:,1]
		precision, recall, thresholds = precision_recall_curve(y_test, y_scores)
		f1 = 2*precision[2:]*recall[2:]/(precision[2:]+recall[2:])
		m_idx = np.argmax(f1)
		# m_thresh += thresholds[2+m_idx]
		threshold[cnt] = thresholds[2+m_idx]
		cnt += 1
		print("%d %f %f" % (precision.shape[0], f1[m_idx], thresholds[2+m_idx]))
	return np.mean(threshold), threshold

# Cross validation using gradient tree boosting
def parametered_cv(x,y,k_fold,k_fold1):
	print("samples: %d %d %d %d" % (x.shape[0],x.shape[1],k_fold,k_fold1))
	kf = StratifiedKFold(y, n_folds=k_fold, shuffle=True, random_state=0)
	index = []
	label = []
	yfit = []
	metrics = np.zeros((k_fold,5),dtype="float32")
	thresholds = []
	predicted = np.array([[0,0]])
	features1 = np.array([[0,0]])
	features2 = np.array([[0,0]])
	thresh = 0.5
	cnt = 0
	print "%d %d" % (sum(y==1), sum(y==0))
	for train_index, test_index in kf:
		x_train, x_test = x[train_index], x[test_index]
		y_train, y_test = y[train_index], y[test_index]
		print y_train.shape
		#print "%d %d" % (sum(y_train==1), sum(y_train==0))
		print("%d %d %d %d" % (x_train.shape[0], x_train.shape[1], x_test.shape[0], x_test.shape[1]))
		if k_fold1>1:
			thresh, thresh_vec = threshold_estimate_cv(x_train,y_train,k_fold1)
		elif k_fold1==1:
			thresh = threshold_estimate(x_train,y_train)
		else:
			thresh = 0.5
		# thresholds = np.concatenate((thresholds,thresh_vec),axis=0)
		# thresh = threshold_estimate(x_train,y_train)
		print("%d %f" % (x_train.shape[0], thresh))
		weight = float(len(y_train[y_train == 0]))/float(len(y_train[y_train == 1]))
		w1 = np.array([1]*y_train.shape[0])
		w1[y_train==1]=weight
		weight1 = float(len(y_test[y_test == 0]))/float(len(y_test[y_test == 1]))
		clf = xgb.XGBClassifier(max_depth=10, learning_rate=0.1, n_estimators=1000, nthread=50)
		#clf = ensemble.GradientBoostingClassifier(**params)
		#clf = RandomForestClassifier(n_estimators=1000)
		clf.fit(x_train, y_train, sample_weight=w1)
		prob = clf.predict_proba(x_test)
		#yfit1 = clf.predict(x_test)
		#score = clf.score(x_test,y_test,sample_weight=w2)
		yfit1 = (prob[:,1]>thresh)
		index = np.concatenate((index,test_index),axis=0)
		label = np.concatenate((label,y_test),axis=0)
		yfit = np.concatenate((yfit,yfit1),axis=0)
		precision, recall, f1, mcc = score_function(y_test,yfit1)
		metrics[cnt,:] = np.array((thresh,precision,recall,f1,mcc))
		print metrics[cnt,:]
		cnt += 1
		predicted = np.concatenate((predicted,prob),axis=0)	
		# print("%d %d: %f %f %f %f" % (label.shape[0],predicted.shape[0],precision,recall,f1,mcc))
		importances, importances_1 = clf.feature_importances_
		indices1 = np.argsort(importances)[::-1]
		feature_1 = np.transpose(np.array((indices1,importances[indices1])))
		features1 = np.concatenate((features1,feature_1),axis=0)
		indices2 = np.argsort(importances_1)[::-1]
		feature_2 = np.transpose(np.array((indices2,importances_1[indices2])))
		features2 = np.concatenate((features2,feature_2),axis=0)
	pred = np.transpose(np.array((index,label,yfit)))
	# np.savetxt('test_epk562com_gradient3thresh2_4ks2.txt', thresholds, fmt='%f', delimiter='\t')
	print "%d %d" % (metrics.shape[0],metrics.shape[1])
	aver_metrics = np.mean(metrics,axis=0)
	print aver_metrics.shape
	aver_metrics = np.reshape(aver_metrics,(1,metrics.shape[1]))
	metrics_1 = np.concatenate((metrics,aver_metrics),axis=0)
	print aver_metrics
	return metrics_1, pred, predicted[1:,], features1[1:,], features2[1:,]

# Single run using gradient tree boosting
def parametered_single(x_train,y_train,x_test,y_test,thresh_opt):
	print("samples: %d %d %d %d" % (x_train.shape[0],x_train.shape[1],x_test.shape[0],x_test.shape[1]))

	metrics = np.zeros((1,5),dtype="float32")
	thresh = 0.5

    # estimate the threshold
	if thresh_opt==1:
		thresh = threshold_estimate(x_train,y_train)

	clf = xgb.XGBClassifier(max_depth=5, learning_rate=0.1, n_estimators=500, nthread=50)
	weight = float(sum(y_train<1))/float(sum(y_train==1))
	w1 = np.array([1]*y_train.shape[0])
	w1[y_train==1]=weight
	clf.fit(x_train, y_train, sample_weight=w1)

	prob = clf.predict_proba(x_test)
	#yfit1 = clf.predict(x_test)
	#score = clf.score(x_test,y_test,sample_weight=w2)
	yfit = (prob[:,1]>thresh)

	precision, recall, f1, mcc = score_function(y_test,yfit)
	metrics = np.array((thresh,precision,recall,f1,mcc))
	print metrics

	importances, importances_1 = clf.feature_importances_
	indices1 = np.argsort(importances)[::-1]
	features1 = np.transpose(np.array((indices1,importances[indices1])))

	pred = np.transpose(np.array((y_test,yfit)))
	return metrics, pred, prob, features1

# Cross validation for PEP-Word
def run_word(word,num_features,k,type,cell):

	warnings.filterwarnings("ignore")
	
	word = int(word)
	num_features = int(num_features)
	k=int(k)
	print "cross_validation_training"

	# Read data
	data = getData(type,cell)

	print "Loading Datavecs"
	dataDataVecs = np.load("./Datavecs/datavecs_"+str(cell)+"_"+str(type)+".npy")
	x = sklearn.preprocessing.StandardScaler().fit_transform(dataDataVecs)
	y = data["label"]
	y = np.asarray(y)
	
	k_fold = 10
	k_fold1 = 0
	serial = 0
	metrics_vec, pred, predicted, features1, features2 = parametered_cv(x,y,k_fold,k_fold1)

	filename1 = "test_%s%s_wordlab.txt"%(str(type), str(cell))
	filename2 = "test_%s%s_wordprob.txt"%(str(type), str(cell))
	filename3 = "test_%s%s_wordfeature.txt"%(str(type), str(cell))
	np.savetxt(filename1, pred, fmt='%d %d %d', delimiter='\t')
	np.savetxt(filename2, predicted, fmt='%f %f', delimiter='\t')
	np.savetxt(filename3, np.concatenate((features1,features2),axis=1), fmt='%d %f %d %f', delimiter='\t')
	filename4 = "test_%s%s_wordthresh.txt"%(str(type), str(cell))
	np.savetxt(filename4, metrics_vec, fmt='%f %f %f %f %f', delimiter='\t')

# Cross validation for PEP-Motif
def run_motif(word, num_features,k,type,cell):

	warnings.filterwarnings("ignore")
	
	word = int(word)
	num_features = int(num_features)
	k=int(k)
	k=int(k)
	print "cross_validation_training"
	print "motif features used"

	# Read data
	data = getData(type,cell)

	filename1 = "/home/yy3/sequences/ep%s_sel_union_balanced_inter_4ks2_add2a.txt"%(str(cell))
	filename2 = "/home/yy3/sequences/ep%s_sel_union_balanced_inter_4ks2_add2a.mat"%(str(cell))
	if(os.path.exists(filename1)==True):
		f = open(filename1, 'r')
		print("Feature importance 1 loaded")
		sel_idx = [map(int,line.split('\t')) for line in f]
		sel_idx = np.ravel(np.asarray(sel_idx))
	elif(os.path.exists(filename2)==True):
		tmp = scipy.io.loadmat(filename2)
		print("Feature importance 2 loaded")
		sel_idx = np.ravel(tmp['sel_vec'])
	else:
		print "Error of file importance file!"

	filename = "/home/yy3/sequences/pairs_%s%s_motif1bn_1_4k.mat"%(str(type),str(cell))
	data = scipy.io.loadmat(filename)
	x1 = np.asmatrix(data['seq_m'])
	y1 = np.ravel(data['lab_m'])
	y1[y1<0]=0
	print "%d %d" % (sum(y1==1), sum(y1==0))
	print "load motif data shuffled"
	filename = "/home/yy3/sequences/pairs_%s%s_motif1bn_1_4kserial.mat"%(str(type),str(cell))
	data1 = scipy.io.loadmat(filename)
	serial1 = np.ravel(data1['serial1'])
	serial2 = np.ravel(data1['serial2'])
	print serial1.shape
	x2 = np.zeros(x1.shape)
	y2 = np.zeros(x1.shape[0])
	print "y1: %d %d" % (sum(y1==1), sum(y1==0))
	print "y2: %d %d" % (sum(y2==1), sum(y2==0))
	x2[serial1,:] = x1
	y2[serial1] = y1
	print "y1: %d %d" % (sum(y2==1), sum(y2==0))
	print "y2: %d %d" % (sum(y2==1), sum(y2==0))
	print "generate motif data shuffled"
	x2 = x2[:,sel_idx]
	#x3 = np.zeros(x1.shape)
	#y3 = np.zeros(x1.shape[0])
	#print "y1: %d %d" % (sum(y1==1), sum(y1==0))
	#print "y3: %d %d" % (sum(y3==1), sum(y3==0))
	#serial3 = np.array(range(0,x1.shape[0]))
	#print serial3.shape
	#random.shuffle(serial3)
	#x3[serial3,:] = x1
	#y3[serial3] = y1
	#print "%d %d %d %d"%(x1.shape[0],x1.shape[1],x3.shape[0],x3.shape[1])
	#print "y1: %d %d" % (sum(y1==1), sum(y1==0))
	#print "y3: %d %d" % (sum(y3==1), sum(y3==0))
	#filename = "/home/yy3/sequences/pairs_%s%s_motif1bn_1_4kshuffle1.mat"%(str(type),str(cell))
	#scipy.io.savemat(filename, mdict={'seq_1':x2,'lab_1':y2,'serial1':serial1,'seq_2':x3,'lab_2':y3,'serial2':serial3})
	
	k_fold = 10
	k_fold1 = 5
	serial = 0
	print "y2: %d %d" % (sum(y2==1), sum(y2==0))
	metrics_vec, pred, predicted, features1, features2 = parametered_cv(x2,y2,k_fold,k_fold1,serial)

	sel_num = 400
	filename1 = "test_%s%s_motiflab_4ks2test1_sel%da.txt"%(str(type), str(cell), sel_num)
	filename2 = "test_%s%s_motifprob_4ks2test1_sel%da.txt"%(str(type), str(cell), sel_num)
	filename3 = "test_%s%s_motiffeature_4ks2test1_sel%da.txt"%(str(type), str(cell), sel_num)
	np.savetxt(filename1, pred, fmt='%d %d %d', delimiter='\t')
	np.savetxt(filename2, predicted, fmt='%f %f', delimiter='\t')
	np.savetxt(filename3, np.concatenate((features1,features2),axis=1), fmt='%d %f %d %f', delimiter='\t')
	# filename4 = "test_epk562_gradient3thresh1_4ks2_add2a1_sel.txt"
	filename4 = "test_%s%s_motifthresh2_4ks2test1_sel%da.txt"%(str(type), str(cell), sel_num)
	np.savetxt(filename4, metrics_vec, fmt='%f %f %f %f %f', delimiter='\t')

# Cross validation for PEP-Integrate
def run_integrate(word, num_features,k,type,cell,sel_num):

	warnings.filterwarnings("ignore")

	word = int(word)
	num_features = int(num_features)
	k=int(k)
	sel_num=int(sel_num)
	print "cross_validation_training"
	print "selected indices: %d"%(int(sel_num))

	# Read data
	#data = getData(type,cell)

	print "Loading Datavecs"
	dataDataVecs = np.load("./Datavecs/datavecs_"+str(cell)+"_"+str(type)+".npy")
	x = sklearn.preprocessing.StandardScaler().fit_transform(dataDataVecs)
	#y = data["label"]
	#y = np.asarray(y)
	#n_vec1 = range(0,x.shape[1]);
	#n_vec2 = range(0,x.shape[1]);
	#random.shuffle(n_vec2);
	#print "%f %f %f"%(x[0,0],x[0,1],x[0,2])
	#x = x[:,n_vec2]
	#print "%f %f %f"%(x[0,0],x[0,1],x[0,2])
	#print y.shape

	filename1 = "/home/yy3/sequences/%s%s_sel_union_balanced_inter_4ks2.txt"%(str(type), str(cell))
	filename2 = "/home/yy3/sequences/%s%s_sel_union_balanced_inter_4ks2.mat"%(str(type), str(cell))
	#filename1 = "/home/yy3/sequences/%s%s_sel_union_balanced_inter_3ks2.txt"%(str(type), str(cell))
	#filename2 = "/home/yy3/sequences/%s%s_sel_union_balanced_inter_3ks2.mat"%(str(type), str(cell))
	if(os.path.exists(filename1)==True):
		f = open(filename1, 'r')
		print("Feature importance 1 loaded")
		sel_idx = [map(int,line.split('\t')) for line in f]
		sel_idx = np.ravel(np.asarray(sel_idx))
	elif(os.path.exists(filename2)==True):
		tmp_idx = scipy.io.loadmat(filename2)
		print("Feature importance 2 loaded")
		sel_idx = np.ravel(tmp_idx['sel_vec'])
	else:
		print "Error of file importance file!"

	filename = "/home/yy3/sequences/pairs_%s%s_motif1bn_1_4k.mat"%(str(type),str(cell))
	#filename = "/home/yy3/sequences/pairs_%s%s_motif1bn_1.mat"%(str(type),str(cell))
	data = scipy.io.loadmat(filename)
	x1 = np.asarray(data['seq_m'])
	y1 = np.ravel(data['lab_m'])
	y1[y1<0]=0
	print "load motif data"
	filename = "/home/yy3/sequences/pairs_%s%s_motif1bn_1_4kserial.mat"%(str(type),str(cell))
	#filename = "/home/yy3/sequences/pairs_%s%s_motif1bn_1_3kserial.mat"%(str(type),str(cell))
	data1 = scipy.io.loadmat(filename)
	serial1 = np.ravel(data1['serial1'])
	serial2 = np.ravel(data1['serial2'])
	print serial2
	x2 = np.zeros(x1.shape)
	y2 = np.zeros(x1.shape[0])
	x2[serial1,:]=x1
	y2[serial1]=y1
	tmp = x2[serial2,:]
	print tmp.shape
	print x.shape

	sel_numvec = np.array([50,100,200,500,600])
	cnt = 0
	for sel_num in sel_numvec:
		print("select_num: %d" % sel_num)

		tmp1 = tmp[:,sel_idx[0:sel_num]]
		print tmp1.shape
		x_2 = np.hstack((x,tmp1))
		#x_2 = x_2[1500:2500,:]
		y_2 = y2[serial2]
		#y_2 = y_2[1500:2500]
		print "%d %d %d %d %d %d"%(x.shape[0],x.shape[1],x1.shape[0],x1.shape[1],x2.shape[0],x2.shape[1])
		print "%d %d" % (sum(y_2==1), sum(y_2==0))
	
		k_fold = 10
		k_fold1 = 5
		metrics_vec, pred, predicted, features1, features2 = parametered_cv(x_2,y_2,k_fold,k_fold1)

		filename1 = "test_%s%s_wordlab_4ks2test_sel%dcv.txt"%(str(type), str(cell), sel_num)
		filename2 = "test_%s%s_wordprob_4ks2test_sel%dcv.txt"%(str(type), str(cell), sel_num)
		filename3 = "test_%s%s_wordfeature_4ks2test_sel%dcv.txt"%(str(type), str(cell), sel_num)
		np.savetxt(filename1, pred, fmt='%d %d %d', delimiter='\t')
		np.savetxt(filename2, predicted, fmt='%f %f', delimiter='\t')
		np.savetxt(filename3, np.concatenate((features1,features2),axis=1), fmt='%d %f %d %f', delimiter='\t')
		filename4 = "test_%s%s_wordthresh2_4ks2test_sel%dcv.txt"%(str(type), str(cell), sel_num)
		np.savetxt(filename4, metrics_vec, fmt='%f %f %f %f %f', delimiter='\t')

# leave out chromosomes for testing for PEP-Integrate
def run_shuffle(word, num_features,k,type,cell,sel_num):

	warnings.filterwarnings("ignore")
	
	word = int(word)
	num_features = int(num_features)
	k = int(k)
	sel_num = int(sel_num)
	print "shuffle features..."

	filename = "/home/yy3/seq_data/sequences/pairs_%s%s_motif1bn_1_4k.mat"%(str(type),str(cell))
	#filename = "/home/yy3/sequences/pairs_%s%s_motif1bn_1.mat"%(str(type),str(cell))
	data = scipy.io.loadmat(filename)
	x1 = np.asarray(data['seq_m'])
	y = np.ravel(data['lab_m'])
	y[y<0]=0
	print "Loading motif data"

	serial3 = np.array(range(0,x1.shape[1]))
	print serial3.shape
	random.shuffle(serial3)
	x = x1[:,serial3]

	print "%d %d %d %d"%(x1.shape[0],x1.shape[1],x.shape[0],x.shape[1])
	print "y: %d %d" % (sum(y==1), sum(y==0))

	filename4 = "test_%s%s_motifidx_4ks2test_shuffle%d.txt"%(str(type), str(cell), sel_num)
	np.savetxt(filename4, np.array((range(0,x1.shape[1]),serial3)).T, fmt='%d %d', delimiter='\t')

	k_fold = 10
	k_fold1 = 0
	metrics_vec, pred, predicted, features1, features2 = parametered_cv(x,y,k_fold,k_fold1)

	filename1 = "test_%s%s_motiflab_4ks2test_shuffle%d.txt"%(str(type), str(cell), sel_num)
	filename2 = "test_%s%s_motifprob_4ks2test_shuffle%d.txt"%(str(type), str(cell), sel_num)
	filename3 = "test_%s%s_motiffeature_4ks2test_shuffle%d.txt"%(str(type), str(cell), sel_num)
	np.savetxt(filename1, pred, fmt='%d %d %d', delimiter='\t')
	np.savetxt(filename2, predicted, fmt='%f %f', delimiter='\t')
	np.savetxt(filename3, np.concatenate((features1,features2),axis=1), fmt='%d %f %d %f', delimiter='\t')

 