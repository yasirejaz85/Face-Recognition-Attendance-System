import cv2
import numpy as np
import os
from datetime import datetime
import pickle
import time

# Path to training images
path = 'Training images'
images = []
classNames = []
myList = os.listdir(path)
print("Training images found:", myList)

# Load training images
for cl in myList:
    curImg = cv2.imread(f'{path}/{cl}')
    if curImg is not None:
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])
    else:
        print(f"Warning: Could not load image {cl}")

print("Loaded class names:", classNames)

# Initialize face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def extract_face_features(img):
    """Extract improved features from face region"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) > 0:
        # Get the largest face
        largest_face = max(faces, key=lambda x: x[2] * x[3])
        x, y, w, h = largest_face
        face_roi = gray[y:y+h, x:x+w]
        
        # Resize to standard size for comparison
        face_roi = cv2.resize(face_roi, (100, 100))
        
        # Apply Gaussian blur to reduce noise
        face_roi = cv2.GaussianBlur(face_roi, (3, 3), 0)
        
        # Extract histogram features with better normalization
        hist = cv2.calcHist([face_roi], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        return hist
    return None

def findEncodings(images):
    """Extract features from all training images"""
    encodeList = []
    valid_images = []
    
    for i, img in enumerate(images):
        features = extract_face_features(img)
        if features is not None:
            encodeList.append(features)
            valid_images.append(classNames[i])
        else:
            print(f"Warning: No face detected in {classNames[i]}")
    
    return encodeList, valid_images

def compare_faces(known_features, face_features, threshold=0.5):
    """Compare face features using correlation with optimized threshold"""
    if face_features is None:
        return False, 0
    
    correlations = []
    for known_feat in known_features:
        corr = cv2.compareHist(known_feat, face_features, cv2.HISTCMP_CORREL)
        correlations.append(corr)
    
    max_corr = max(correlations)
    best_match = correlations.index(max_corr)
    
    # Print correlation values for debugging (only when significant)
    if max_corr > 0.4:
        print(f"Best match: {validClassNames[best_match] if best_match < len(validClassNames) else 'Unknown'} with correlation: {round(max_corr, 3)}")
    
    # Additional check: ensure the best match is significantly better than others
    if max_corr > threshold:
        # Check if the best match is at least 0.1 better than the second best
        correlations_sorted = sorted(correlations, reverse=True)
        if len(correlations_sorted) > 1:
            difference = correlations_sorted[0] - correlations_sorted[1]
            if difference < 0.1:  # If difference is too small, it's ambiguous
                return False, best_match
    
    return max_corr > threshold, best_match

# Attendance tracking system - one attendance per person per day

def markAttendance(name):
    """Mark attendance in CSV file - only once per person per day"""
    try:
        now = datetime.now()
        today = now.strftime("%m/%d/%Y")
        dtString = now.strftime("%m/%d/%Y,%H:%M:%S")
        
        # Check if person already marked attendance today
        try:
            with open('Attendance.csv', 'r') as f:
                lines = f.readlines()
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            person_name = parts[0]
                            date_part = parts[1].split(',')[0] if ',' in parts[1] else parts[1]
                            if person_name == name and date_part == today:
                                print(f"Attendance already marked for {name} today")
                                return  # Already marked today
        except FileNotFoundError:
            pass  # File doesn't exist yet, create it
        
        # Mark attendance for today
        with open('Attendance.csv', 'a') as f:
            f.write(f'{name},{dtString}\n')
        
        print(f"Attendance marked for {name} at {dtString}")
        
    except PermissionError:
        # Wait a moment and try again with the same file
        time.sleep(0.1)
        try:
            now = datetime.now()
            today = now.strftime("%m/%d/%Y")
            dtString = now.strftime("%m/%d/%Y,%H:%M:%S")
            
            # Check again if person already marked attendance today
            try:
                with open('Attendance.csv', 'r') as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Skip header
                        if line.strip():
                            parts = line.strip().split(',')
                            if len(parts) >= 2:
                                person_name = parts[0]
                                date_part = parts[1].split(',')[0] if ',' in parts[1] else parts[1]
                                if person_name == name and date_part == today:
                                    print(f"Attendance already marked for {name} today")
                                    return  # Already marked today
            except FileNotFoundError:
                pass  # File doesn't exist yet, create it
            
            # Mark attendance for today
            with open('Attendance.csv', 'a') as f:
                f.write(f'{name},{dtString}\n')
            
            print(f"Attendance marked for {name} at {dtString}")
        except:
            print(f"Could not mark attendance for {name} - file busy")

# Extract features from training images
print("Extracting features from training images...")
encodeListKnown, validClassNames = findEncodings(images)
print(f'Encoding Complete. {len(encodeListKnown)} faces encoded')

if len(encodeListKnown) == 0:
    print("No faces found in training images. Please check your training images.")
    exit()

# Initialize webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam")
    exit()

print("Starting face recognition... Press 'q' to quit")

while True:
    success, img = cap.read()
    if not success:
        print("Error: Could not read from webcam")
        break
    
    # Resize for faster processing
    imgS = cv2.resize(img, (0, 0), None, 0.5, 0.5)
    
    # Detect faces in current frame
    gray = cv2.cvtColor(imgS, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    for (x, y, w, h) in faces:
        # Scale back to original size
        x, y, w, h = x * 2, y * 2, w * 2, h * 2
        
        # Make the frame bigger for better screenshots
        padding = 20
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(img.shape[1] - x, w + 2 * padding)
        h = min(img.shape[0] - y, h + 2 * padding)
        
        # Extract features from detected face
        face_roi = img[y:y+h, x:x+w]
        face_features = extract_face_features(face_roi)
        
        if face_features is not None:
            # Compare with known faces
            is_match, match_index = compare_faces(encodeListKnown, face_features)
            
            if is_match and match_index < len(validClassNames):
                name = validClassNames[match_index].upper()
                
                # Draw bigger rectangle and name for better screenshots
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 4)
                cv2.rectangle(img, (x, y + h - 50), (x + w, y + h), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, name, (x + 10, y + h - 15), cv2.FONT_HERSHEY_COMPLEX, 1.2, (255, 255, 255), 3)
                
                # Mark attendance
                markAttendance(name)
            else:
                # Unknown face - always show UNKNOWN for unrecognized faces
                display_name = "UNKNOWN"
                
                # Draw bigger rectangle and name for better screenshots
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 4)
                cv2.rectangle(img, (x, y + h - 50), (x + w, y + h), (0, 0, 255), cv2.FILLED)
                cv2.putText(img, display_name, (x + 10, y + h - 15), cv2.FONT_HERSHEY_COMPLEX, 1.2, (255, 255, 255), 3)
    
    # Display the image
    cv2.imshow('Face Recognition Attendance System', img)
    
    # Break loop on 'q' press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()
print("Face recognition system stopped.")
