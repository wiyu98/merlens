import cv2
import dlib
import numpy as np
from imutils import face_utils
import pyautogui
import keyboard
import time
import speech_to_text

face_landmark_path = './shape_predictor_68_face_landmarks.dat'

with np.load('HD920.npz') as X:
    K, D = [X[i] for i in ('mtx','dist')] 

cam_matrix = np.array(K).reshape(3, 3).astype(np.float32)
dist_coeffs = np.array(D).reshape(5, 1).astype(np.float32)

object_pts = np.float32([[6.825897, 6.760612, 4.402142],
                         [1.330353, 7.122144, 6.903745],
                         [-1.330353, 7.122144, 6.903745],
                         [-6.825897, 6.760612, 4.402142],
                         [5.311432, 5.485328, 3.987654],
                         [1.789930, 5.393625, 4.413414],
                         [-1.789930, 5.393625, 4.413414],
                         [-5.311432, 5.485328, 3.987654],
                         [2.005628, 1.409845, 6.165652],
                         [-2.005628, 1.409845, 6.165652],
                         [2.774015, -2.080775, 5.048531],
                         [-2.774015, -2.080775, 5.048531],
                         [0.000000, -3.116408, 6.097667],
                         [0.000000, -7.415691, 4.070434]])

reprojectsrc = np.float32([[10.0, 10.0, 10.0],
                           [10.0, 10.0, -10.0],
                           [10.0, -10.0, -10.0],
                           [10.0, -10.0, 10.0],
                           [-10.0, 10.0, 10.0],
                           [-10.0, 10.0, -10.0],
                           [-10.0, -10.0, -10.0],
                           [-10.0, -10.0, 10.0]])

line_pairs = [[0, 1], [1, 2], [2, 3], [3, 0],
              [4, 5], [5, 6], [6, 7], [7, 4],
              [0, 4], [1, 5], [2, 6], [3, 7]]


def get_head_pose(shape):
    image_pts = np.float32([shape[17], shape[21], shape[22], shape[26], shape[36],
                            shape[39], shape[42], shape[45], shape[31], shape[35],
                            shape[48], shape[54], shape[57], shape[8]])

    _, rotation_vec, translation_vec = cv2.solvePnP(object_pts, image_pts, cam_matrix, dist_coeffs)

    reprojectdst, _ = cv2.projectPoints(reprojectsrc, rotation_vec, translation_vec, cam_matrix,
                                        dist_coeffs)

    reprojectdst = tuple(map(tuple, reprojectdst.reshape(8, 2)))

    # calc euler angle
    rotation_mat, _ = cv2.Rodrigues(rotation_vec)
    pose_mat = cv2.hconcat((rotation_mat, translation_vec))
    _, _, _, _, _, _, euler_angle = cv2.decomposeProjectionMatrix(pose_mat)
    pose_mat = np.concatenate((pose_mat, np.array([[0,0,0,1]])), axis=0)

    return reprojectdst, euler_angle, pose_mat


def main():
    # return
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Unable to connect to camera.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(face_landmark_path)

    screenWidth, screenHeight = pyautogui.size()

    x_range = (-.2, .3)
    y_range = (-.1, .05)

    num_points_to_average = 5

    exp_factor = -1

    delta_slow = .2
    delta_fast = .49

    speed_scale_factor_slow = 1
    speed_scale_factor_fast = 3

    x_list = []
    y_list = []

    mouse_x = .5
    mouse_y = .5

    blinkTog = False

    eyeClose = False

    eye_close_timer = None
    
    baseVal = None

    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            face_rects = detector(frame, 0)

            if keyboard.is_pressed('b'):
                eyeClose = True
            else:
                eyeClose = False

            if len(face_rects) > 0:
                shape = predictor(frame, face_rects[0])
                shape = face_utils.shape_to_np(shape)

                reprojectdst, euler_angle, pose_mat = get_head_pose(shape)
                forward_face_vec = pose_mat[0:3, 2]

                # print(forward_face_vec)

                x = (x_range[1] - forward_face_vec[0]) / (x_range[1] - x_range[0])
                y = (y_range[1] - forward_face_vec[1]) / (y_range[1] - y_range[0])
                x = max(min(x, 1), 0)
                y = max(min(y, 1), 0)

                # print(x,y)

                x_list.append(x)
                y_list.append(y)

                if len(x_list) > num_points_to_average:
                    x_list.pop(0)
                    y_list.pop(0)

                x_arr = np.flip(np.array(x_list))
                y_arr = np.flip(np.array(y_list))

                weighting = np.exp(exp_factor * np.arange(x_arr.shape[0]))
                weighting = weighting / np.sum(weighting)

                x_smoothed = np.dot(x_arr, weighting)
                y_smoothed = np.dot(y_arr, weighting)

                

                pyautogui.moveTo(mouse_x * screenWidth, 
                                 mouse_y * screenHeight)
                

                important = [36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
                eyeY = 0
                eyeX = 0
                nose = [27, 28, 29, 30]
                noseY = 0
                noseX = 0
                ds = dict()
                for index in important:
                    (x, y) = shape[index]
                    ds[index] = y
                    eyeY += y
                    eyeX += x
                eyeY //= 8
                eyeX //= 8
                for index in nose:
                    (x, y) = shape[index]
                    noseY += y
                    noseX += x
                noseY //= 4
                noseX //= 4
                cv2.circle(frame, (eyeX, eyeY), 1, (255, 0, 0), -1)
                cv2.circle(frame, (noseX, noseY), 1, (255, 0, 0), -1)

                if baseVal == None:
                    baseVal = noseY - eyeY

                eyeClose1 = ((ds[41] - ds[37] < 6.5) and
                            (ds[40] - ds[38] < 6.5) and
                            (ds[47] - ds[43] < 6.5) and
                            (ds[46] - ds[44] < 6.5))

                eyeClose2 = (noseY - eyeY < baseVal * (5 / 6))

                def calcEAR(pts):
                    (x1, y1) = pts[0]
                    (x2, y2) = pts[1]
                    (x3, y3) = pts[2]
                    (x4, y4) = pts[3]
                    (x5, y5) = pts[4]
                    (x6, y6) = pts[5]
                    (v1x, v1y) = (x2 - x6, y2 - y6)
                    (v2x, v2y) = (x3 - x5, y3 - y5)
                    (v3x, v3y) = (x1 - x4, y1 - y4)
                    piece1 = np.sqrt((v1x**2) + (v1y**2))
                    piece2 = np.sqrt((v2x**2) + (v2y**2))
                    piece3 = np.sqrt((v3x**2) + (v3y**2))
                    return (piece1 + piece2) / (2 * piece3)

                EARL = calcEAR(shape[36:42])
                EARR = calcEAR(shape[42:48])

                eyeClose3 = ((EARL < 0.2) and (EARR < 0.2))

                if eyeClose3: blinkTog = not blinkTog

                if blinkTog: 
                    color = (0, 255, 0)
                else: 
                    color = (0, 0, 255)

                for i in important:
                    (x, y) = shape[i]
                    cv2.circle(frame, (x, y), 1, color, -1)

                for i in nose:
                    (x, y) = shape[i]
                    cv2.circle(frame, (x, y), 1, color, -1)

                for start, end in line_pairs:
                    cv2.line(frame, reprojectdst[start], reprojectdst[end], color)

                if abs(x_smoothed - .5) > delta_slow and not eyeClose3:
                    if abs(x_smoothed - .5) > delta_fast:
                        scale = speed_scale_factor_fast
                    else:
                        scale = speed_scale_factor_slow
                    scale = scale * (abs(x_smoothed - .5) - delta_slow) / abs(x_smoothed - .5)
                    x_diff = ((x_smoothed - .5) ** 5) * scale
                    mouse_x += x_diff
                if abs(y_smoothed - .5) > delta_slow and not eyeClose3:
                    if abs(y_smoothed - .5) > delta_fast:
                        scale = speed_scale_factor_fast
                    else:
                        scale = speed_scale_factor_slow
                    scale = scale * (abs(y_smoothed - .5) - delta_slow) / abs(y_smoothed - .5)
                    y_diff = ((y_smoothed - .5) ** 5) * scale
                    mouse_y += y_diff

                if eyeClose3 and eye_close_timer is None:
                    eye_close_timer = time.time()
                elif not eyeClose3 and eye_close_timer is not None:
                    time_closed = time.time() - eye_close_timer
                    if time_closed > 3:
                        print("typing")
                        print("\a")
                        text = speech_to_text.detect_sentence()
                        if text[-5:].lower() == "enter":
                            text = text[:-5] + "\n"
                        pyautogui.typewrite(text)
                    elif time_closed > 1:
                        print("click")
                        pyautogui.click()
                    eye_close_timer = None

            # cv2.imshow("demo", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

if __name__ == '__main__':
    main()