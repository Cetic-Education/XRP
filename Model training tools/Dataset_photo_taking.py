import cv2
import os

def save_frame_safely(frame, folder_path='./img'):

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")


    i = 0
    while True:
        filename = os.path.join(folder_path, f"{i}.png")
        if not os.path.exists(filename):
            break
        i += 1
    
    cv2.imwrite(filename, frame)
    print(f"Image saved: {filename}")

def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Cannot open camera")
        return

    print("Press [space] to save image")
    print("Press [ESC] or [q] to exit")

    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("Cannot receive new frame (stream end?). Exiting ...")
            break

        cv2.imshow('Camera Preview', frame)

        key = cv2.waitKey(1) & 0xFF

# Space pressed
        if key == 32:
            save_frame_safely(frame)
# q/ esc pressed
        elif key == 27 or key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
