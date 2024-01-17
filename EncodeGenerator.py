import cv2
import face_recognition
import pickle
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage

cred = credentials.Certificate("service_account_key.json")# it should be your service account key
firebase_admin.initialize_app(cred,{
    'databaseURL': "your data base url ",
    'storageBucket': "your storage bucket url "
})

folderPath='Images'
pathList=os.listdir(folderPath)
print(pathList)
imgList=[]
studentIds=[]

for path in pathList:
    imgList.append(cv2.imread(os.path.join(folderPath,path)))
    studentIds.append(os.path.splitext(path)[0])
    fileName= f'{folderPath}/{path}'
    bucket = storage.bucket()
    blob=bucket.blob(fileName)
    blob.upload_from_filename(fileName)
    #print(path)
    #print(os.path.splitext(path)[0])
print(studentIds)
def findEncodings(imageList):
    encodeList=[]
    for img in imageList:
        img=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        encode=face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList
print("Encoding started")
encodeListKnown=findEncodings(imgList)
encodeListKnownWithIds=[encodeListKnown,studentIds]
print("Encoding Complete")

file=open("EncodeFile.p",'wb')
pickle.dump(encodeListKnownWithIds,file)
file.close()
print("MASTER ARHAN FILE HAS BEEN SAVED")
