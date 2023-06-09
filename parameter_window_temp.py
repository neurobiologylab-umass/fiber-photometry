from PyQt5.QtWidgets import QLabel, QMainWindow, QApplication, QPushButton, QDialogButtonBox
from PyQt5.QtGui import QPixmap
from PyQt5 import uic
import cv2
import sys
import qimage2ndarray


class ParameterWindow(QMainWindow):
    def __init__(self):
        super(ParameterWindow, self).__init__()

        # Load the ui file generated by QtDesigner
        uic.loadUi("parameter_window.ui", self)
        
        self.update_img_btn = self.findChild(QPushButton, "updateImageButton")
        self.roi_btn = self.findChild(QPushButton, "ROIButton")
        self.img_display = self.findChild(QLabel, "imageDisplay")
        self.buttonBox = self.findChild(QDialogButtonBox, )

        self.update_img_btn.clicked.connect(self.update_img)
        self.roi_btn.clicked.connect(self.roi)
        self.buttonBox.accepted.connect(self.param_selected)
        self.buttonBox.rejected.connect(self.param_selected)

        self.is_ROI_selected = False
        self.is_param_selected = False

        self.show()
    
    def update_img(self):
        if self.is_ROI_selected == True:
            # Selects whatever the primary camera on the device is
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # 2nd arg removes warning
            _, img=cap.read()
            img_crop = img[self.roi_xmin:self.roi_xmax, 
                           self.roi_ymin:self.roi_ymax]
            # Opencv uses bgr colors, we convert since QImage uses rgb
            img_rgb = cv2.cvtColor(img_crop, cv2.COLOR_BGR2RGB)
            # Opencv creates a numpy array, but QPixmap requires a QImage
            qImg = qimage2ndarray.array2qimage(img_rgb)
            # Display the image in the label widget of the GUI
            self.img_display.setPixmap(QPixmap(qImg))
        else:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 
            _, img=cap.read()
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            qImg = qimage2ndarray.array2qimage(img_rgb)
            self.img_display.setPixmap(QPixmap(qImg))


    def roi(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        _, img=cap.read()
        try:
            roi = cv2.selectROI(img)
            self.roi_xmin, self.roi_xmax = int(roi[1]), int(roi[1] + roi[3])
            self.roi_ymin, self.roi_ymax = int(roi[0]), int(roi[0] + roi[2])
            # Crop the image using the user selected roi
            img_crop = img[self.roi_xmin:self.roi_xmax, 
                           self.roi_ymin:self.roi_ymax]
            # If the user has selected a roi, close the original window
            if self.roi_xmax > 0 or self.roi_ymax > 0:
                cv2.destroyAllWindows()
            # Wait infinitely until the user presses a key
            cv2.waitKey(0)
            # Show the cropped image in a new window
            cv2.imshow("Image", img_crop)
            self.is_ROI_selected = True
        except:
            cv2.destroyAllWindows()
            self.is_ROI_selected = False
    
    def param_selected(self):
        self.is_param_selected = True
        self.close()
    
    def no_param_selected(self):
        self.is_param_selected = False
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    UIWindow = ParameterWindow()
    app.exec_()