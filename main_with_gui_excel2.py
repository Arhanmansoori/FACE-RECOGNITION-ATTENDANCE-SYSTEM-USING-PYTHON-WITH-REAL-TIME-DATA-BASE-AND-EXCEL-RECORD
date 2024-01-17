#install all the libraries .... using pip install name of library

import os
import pickle 
import cv2
import face_recognition
import numpy as np
import cvzone
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
#python image library
import threading        #Python threading allows you to have different parts of your program run concurrently and can simplify your design.
import openpyxl                       #the use of threading here is to ensure that the face recognition process (start_recognition) runs in a separate thread from the main Tkinter GUI thread


cred = credentials.Certificate("service_account_key.json")# download service account key by creating your project on firebase 
firebase_admin.initialize_app(cred, {
    'databaseURL': "your data base link ",# your database should be created on firebase console 
    'storageBucket': "your storage bucket link "# images should be uploaded on storage bucket 
})  # your database and storage bucket url should be feeded above 
bucket = storage.bucket()

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)
imgBackground = cv2.imread('Resources/background.png')

folderModePath = 'Resources/Modes'
modePathList = os.listdir(folderModePath)
imgModeList = [cv2.imread(os.path.join(folderModePath, path)) for path in modePathList]

print("loading encode file MASTER ARHAN ")
file = open('EncodeFile.p', 'rb')   #rb read binary 
#Binary files are those that contain non-text data, such as images, audio, or serialized objects. 
encodeListKnownWithIds = pickle.load(file)
file.close()
encodeListKnown, studentIds = encodeListKnownWithIds
print("Encode file loaded successfully MASTER ARHAN")

modeType = 0
counter = 0
id = -1
imgStudent = []

# Create an Excel workbook and set up the worksheet
wb = openpyxl.Workbook()
ws = wb.active
ws.append(["ID", "Name", "Total Attendance", "Last Attendance Time"])

# Dictionary to store the last attendance time for each student
last_attendance_time_dict = {}

def start_recognition():
    global imgBackground, modeType, counter, id, imgStudent

    while True:
        success, img = cap.read()
        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

        imgBackground[162:162 + 480, 55:55 + 640] = img  # coordinates at which coordinate the camera frame will be fitting 
        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

        if faceCurFrame:
            for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                #Face dis computes the Euclidean distances between the current face (x2-x1)^2+(y2-y1)^2
                '''encodeFace: The face encoding of the current face detected in the video frame.
                encodeListKnown[matchIndex]: The face encoding from the 
                list of known face encodings that has the smallest distance to the current face.'''
                matchIndex = np.argmin(faceDis)# built to find the starting point of the range
                if matches[matchIndex]:
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                    #bbox  bounding box   bounding box is a rectangular box that encompasses an object or a region of interest within an image
                    imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                    id = studentIds[matchIndex]

                    # Check if attendance can be marked
                    if can_mark_attendance(id):
                        print(f"Attendance marked for ID: {id}")
                        cvzone.putTextRect(imgBackground, "Loading", (275, 400))
                        cv2.imshow("Face Attendance", imgBackground)
                        cv2.waitKey(1)
                        counter = 1
                        modeType = 1

                        # Write attendance to Excel file
                        student_info = db.reference(f'Students/{id}').get()
                        datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ws.append([id, student_info['name'], student_info['total_attendance'], datetime_now])
                        wb.save("attendance_record.xlsx")

                        # Update the last attendance time in the dictionary
                        last_attendance_time_dict[id] = datetime.now()

            if counter != 0:
                if counter == 1:
                    student_info = db.reference(f'Students/{id}').get()
                    blob = bucket.get_blob(f'Images/{id}.png')
                    array = np.frombuffer(blob.download_as_string(), np.uint8)
                    imgStudent = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)

                    attendance_marked = False

                    datetimeObject = datetime.strptime(student_info['last_attendance_time'],
                                                     "%Y-%m-%d %H:%M:%S")
                    secondsElapsed = (datetime.now() - datetimeObject).total_seconds()

                    if secondsElapsed > 30:
                        ref = db.reference(f'Students/{id}')
                        student_info['total_attendance'] += 1
                        ref.child('total_attendance').set(student_info['total_attendance'])
                        ref.child('last_attendance_time').set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        modeType = 3
                        counter = 0
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                if modeType != 3:
                    if 10 < counter < 20:
                        modeType = 2

                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                    if counter <= 10: #This implies that this section of code is meant to execute during the first 10 frames after a face is recognized.
                        cv2.putText(imgBackground, str(student_info['total_attendance']), (861, 125),
                                    cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)

                        cv2.putText(imgBackground, str(student_info['major']), (1006, 550),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)

                        cv2.putText(imgBackground, str(id), (1006, 493),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)

                        cv2.putText(imgBackground, str(student_info['standing']), (910, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (255, 255, 255), 1)

                        cv2.putText(imgBackground, str(student_info['year']), (1025, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)

                        cv2.putText(imgBackground, str(student_info['starting_year']), (1125, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                        (w, h), _ = cv2.getTextSize(student_info['name'], cv2.FONT_HERSHEY_COMPLEX, 1, 1) #  Calculates the size and offset for the student's name to ensure proper placement on the GUI.
                                                                                 #(w, h) This is a tuple representing the width (w) and height (h) of the bounding box that would enclose the text.
                        offset = (414 - w) // 2

                        cv2.putText(imgBackground, str(student_info['name']), (808 + offset, 445),
                                    cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)

                        imgBackground[175:175 + 216, 909:909 + 216] = imgStudent  #Replaces a region on the imgBackground image with the image of the recognized student 

                    counter += 1

                    if counter >= 20:
                        counter = 0
                        modeType = 0
                        student_info = []
                        imgStudent = []
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
        else:
            modeType = 0
            counter = 0

        cv2.imshow("Face Attendance", imgBackground)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def update_gui():
    _, img = cap.read()
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (640, 480))
    img = Image.fromarray(img)
    img = ImageTk.PhotoImage(image=img)

    label_webcam.imgtk = img
    label_webcam.configure(image=img)

    root.update()

    root.after(10, update_gui)

def close_face_recognition():
    global cap
    cap.release()
    root.destroy()

# Function to check if attendance can be marked for a student
def can_mark_attendance(student_id):
    if student_id in last_attendance_time_dict:
        datetimeObject = last_attendance_time_dict[student_id]
        secondsElapsed = (datetime.now() - datetimeObject).total_seconds()
        return secondsElapsed > 30
    else:
        return True

# Create a Tkinter window
root = tk.Tk()
root.title("Face Recognition Attendance System by Arhan mansoori pvt.Ltd")
root.geometry("800x600")

# Create a label for displaying webcam feed
label_webcam = tk.Label(root)
label_webcam.pack(padx=10, pady=10)

# Create a start button
start_button = tk.Button(root, text="Start Recognition", command=lambda: threading.Thread(target=start_recognition).start())
start_button.pack(pady=10)

# Create a close button
close_button = tk.Button(root, text="Close Face Recognition", command=close_face_recognition)
close_button.pack(pady=10)

# Function to update the GUI
root.after(10, update_gui) #10 milliseconds in loop
root.mainloop()

'''n the context of machine learning and computer vision, "encoding" typically refers to the process of converting data or information into a specific format or representation
 that is suitable for a particular task. The purpose of encoding is to transform the original data into a more efficient, compact, or standardized form that can be easily processed or interpreted by a machine learning model or algorithm.'''
