import cv2

for i in range(10):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)

    if cap.isOpened():
        ret, frame = cap.read()

        if ret:
            print(
                f"Camera {i} : "
                f"{frame.shape[1]}x{frame.shape[0]}"
            )

        cap.release()