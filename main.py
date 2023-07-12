

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QApplication,
    QPushButton,
    QMessageBox,QGridLayout, QLabel, QLineEdit
)
from pyqtgraph import PlotWidget, mkPen
from main_ui import MainUI
import sys
import pyqtgraph as pg
import cv2
import numpy as np
import pandas as pd
from collections import deque
import time
import datetime
import os
import csv
import PySpin
from PIL import Image
import qimage2ndarray
# import pyqtgraph as pg
from scipy.stats import zscore
import nidaqmx
from nidaqmx.constants import AcquisitionType
from pathlib import Path, PureWindowsPath
# from parameter_window import ParameterWindow
# from experiment_setup import Settings
from flir import RecordingWorker, FLIRAcquisitionWorker, ROI


# uiclass, baseclass = pg.Qt.loadUiType("main.ui")
# If changes are made in QtDesigner, open cmd in main.ui folder and execute:
# pyside2-uic main.ui -o MainWindow.py
#connector 0: ao0 camera, ao1 405 (on labview channels 1,2) 
#connector 1: ao0 470, ao1 625 (on labview channels 3,4)

class Main(QMainWindow):
    def __init__(self, parent=None):
        super(Main, self).__init__(parent=parent)
        ui = MainUI()
        ui.setupUi(self)

        # Customize title and icon in window corner
        self.setWindowTitle("NBI Photometry")
        self.setWindowIcon(QtGui.QIcon('nbi-logo.jpg'))

        # .....
        self.txt_name = self.findChild(QLineEdit,"txt_name")
        self.btn_roi = self.findChild(QPushButton, "btn_roi")
        self.btn_exp_init = self.findChild(QPushButton, "btn_exp_init")        
        self.btn_plot = self.findChild(QPushButton, "btn_plot")
        self.btn_record = self.findChild(QPushButton, "btn_record")
        self.btn_stop = self.findChild(QPushButton, "btn_stop")
        self.img_display = self.findChild(QLabel, "img_display")

        self.plot_final = self.findChild(PlotWidget, "plot_final")
        self.plot_chn1 = self.findChild(PlotWidget, "plot_chn1")
        self.plot_chn2 = self.findChild(PlotWidget, "plot_chn2")
        self.plot_chn3 = self.findChild(PlotWidget, "plot_chn3")


        # Link buttons to ...
        self.btn_exp_init.clicked.connect(self.init_experiment)        
        self.btn_roi.clicked.connect(self.select_roi)
        self.btn_plot.clicked.connect(self.plotting)
        self.btn_record.clicked.connect(self.recording)
        self.btn_stop.clicked.connect(self.stop)

        # Flag for ....
        self.is_experiment_initialized = False
        self.roi = None         
        self.rec_worker = None        
        self.acq_worker = None  
        self.plot_timer = None
        

        self.init_plotting_recording()
        self.show()
        
    def init_plotting_recording(self):
        # Flags for whether or not the user is plotting and recording
        self.is_plotting = False #self.deque_acq,  deque([]), self.deque_record,deque([]), 
        self.deque_recording, self.deque_plotting =deque([]), deque([])
        self.iterator = 0
        self.t0 = 0
        
        # Set labels, colors, ranges for each plot widget
        self.plot_chn1.setLabel("bottom", "Time since start (s)")
        self.plot_chn1.setLabel("left", "Intensity")
        self.plot_chn2.setLabel("bottom", "Time since start (s)")
        self.plot_chn2.setLabel("left", "Intensity")
        self.plot_chn3.setLabel("bottom", "Time since start (s)")
        self.plot_chn3.setLabel("left", "Intensity")
        self.plot_final.setLabel("bottom", "Time since start (s)")
        self.plot_final.setLabel("left", "Intensity")
        self.plot_final.hide()

        self.pen1 = mkPen(color=(0, 255, 0))
        self.plot_chn1.setYRange(-6,6)
        self.pen2 = mkPen(color=(0, 0, 255))
        self.plot_chn2.setYRange(-6,6)
        self.pen3 = mkPen(color=(255, 0, 255))
        self.plot_chn3.setYRange(-6,6)
        self.pen4 = mkPen(color =(255, 140, 0))
        self.plot_final.setYRange(-6,6)

        # Limits the number of data points shown on the graph
        self.graph_lim = 100
        """
        First deque will be used to quickly store time and image data, then 
        the data will be passed into the plot deque, which is used for 
        computation and plotting
        """
        self.deque_timesteps1 = deque([], maxlen=self.graph_lim)
        self.deque_timesteps2 = deque([], maxlen=self.graph_lim)
        self.deque_timesteps3 = deque([], maxlen=self.graph_lim)
        self.deque_sequence1 = deque([], maxlen=self.graph_lim)
        self.deque_sequence2 = deque([], maxlen=self.graph_lim)
        self.deque_sequence3 = deque([], maxlen=self.graph_lim)

    # def init_plotting_recording1(self):
    #     # Initiate double ended queues, store globally so they can be accessed between classes
    #     global record_deque, acq_deque
    #     record_deque = deque([])
    #     acq_deque = deque([])
    #     self.iterator = 0
    #     global img_deque, img_plot_deque
    #     img_deque = deque([])
    #     img_plot_deque = deque([])
    #     self.t0 = 0

    #     # Limits the number of data points shown on the graph
    #     self.graph_lim = 100
    #     # Use deque to store data, fast with threadsafe append and popleft
    #     self.deque_timestamp0 = deque([])
    #     self.deque_timestamp1 = deque([])
    #     self.deque_timestamp2 = deque([])
    #     self.deque_sum_470 = deque([])
    #     self.deque_sum_405 = deque([])
    #     self.deque_sum_590 = deque([])
    #     """
    #     First deque will be used to quickly store time and image data, then 
    #     the data will be passed into the plot deque, which is used for 
    #     computation and plotting
    #     """
    #     self.deque_plot_timestamp_405 = deque([], maxlen=self.graph_lim)
    #     self.deque_plot_timestamp_470 = deque([], maxlen=self.graph_lim)
    #     self.deque_plot_timestamp_590 = deque([], maxlen=self.graph_lim)
    #     self.deque_plot_470 = deque([], maxlen=self.graph_lim)
    #     self.deque_plot_405 = deque([], maxlen=self.graph_lim)
    #     self.deque_plot_590 = deque([], maxlen=self.graph_lim)
    #     self.deque_plot_diff = deque([], maxlen=self.graph_lim)
    #     self.current_470, self.current_405 = 0, 0

    #     # Get pyqtgraph plot widgets from main window and set labels
    #     # Top plot

    #     x1_axis = self.plot_final.getAxis("bottom")
    #     x1_axis.setLabel(text="Time since start (s)")
    #     y1_axis = self.plot_final.getAxis("left")
    #     y1_axis.setLabel(text="Z-score")
    #     # self.plot_final.setYRange(-5,5)
    #     self.plot_final.setYRange(-6,6)

    #     # Set plot line color to green
    #     self.pen_filtered_signal = pg.mkPen(color=(0, 255, 0))

    #     # Bottom left plot
        
    #     x2_axis = self.plot_chn2.getAxis("bottom")
    #     x2_axis.setLabel(text="Time since start (s)")
    #     y2_axis = self.plot_chn2.getAxis("left")
    #     y2_axis.setLabel(text="Intensity")
    #     # Set plot line color to blue
    #     self.pen_470 = pg.mkPen(color=(0, 0, 255))
    #     self.plot_chn2.setYRange(-6,6)

    #     # Bottom right plot
        
    #     x3_axis = self.plot_chn1.getAxis("bottom")
    #     x3_axis.setLabel(text="Time since start (s)")
    #     y3_axis = self.plot_chn1.getAxis("left")
    #     y3_axis.setLabel(text="Intensity")
    #     # Set plot line color to purple
    #     self.pen_405 = pg.mkPen(color=(255, 0, 255))
    #     self.plot_chn1.setYRange(-6,6)

    #     #third plot

        
    #     x4_axis = self.plot_chn3.getAxis("bottom")
    #     x4_axis.setLabel(text = "Time since start (s)")
    #     y4_axis = self.plot_chn3.getAxis("left")
    #     y4_axis.setLabel(text = "Intensity")
    #     #set plot line color to orange
    #     self.pen_590 = pg.mkPen(color =(255, 140, 0))
    #     self.plot_chn3.setYRange(-6,6)


    def init_experiment(self):
        experimenter_name = self.txt_name.text()   
         
        if not experimenter_name:
            QMessageBox.critical(self, "Error", "Please enter the experimenter's name")
            return
        
        if self.roi is None:
            QMessageBox.critical(self, "Error", "Please select the region of interest")
            return



        folder_name = f"{experimenter_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        folder_path = os.path.join(os.getcwd(), "data", folder_name)

        try:
            os.mkdir(folder_path)
        except OSError:
            QMessageBox.critical(self, "Error", "Failed to create experiment folder")
            return

        self.experiment_data_path = os.path.join(folder_path, "ExperimentData.csv")
        # with open(self.experiment_data_path, "w") as file:
        #     writer = csv.writer(file)
        #     header = ["Timestamp", "Sum Fluorescence (405nm)", "Sum Fluorescence (470nm)", "Sum Fluorescence (590nm)"]
        #     writer.writerow(header)

        # self.experiment_info_path = os.path.join(folder_path, "ExperimentInfo.csv")
        # with open(self.experiment_info_path, "w") as file:
        #     writer = csv.writer(file)
        #     header = [
        #         "Experiment Date and Time",
        #         "Recording Start Time",
        #         "Recording End Time",
        #         "Sampling Rate",
        #         "Exposure",
        #         "ROI_XMIN",
        #         "ROI_XMAX",
        #         "ROI_YMIN",
        #         "ROI_YMAX",
        #         "ROI_XRANGE",
        #         "ROI_YRANGE",
        #     ]
        #     writer.writerow(header)

        self.images_folder_path = os.path.join(folder_path, "images")
        os.mkdir(self.images_folder_path)
        self.is_experiment_initialized = True
        QMessageBox.information(self, "Success", "New experiment has been successfully initialized.")

    def select_roi(self):
        if self.acquire_image():
            try:
                img = cv2.cvtColor(self.image, cv2.COLOR_BAYER_BG2RGB)
                # img = self.image
                roi = cv2.selectROI(img)
                self.roi = ROI(roi)
                img_crop = img[self.roi.xmin:self.roi.xmax, self.roi.ymin:self.roi.ymax]

                # Convert the OpenCV image to QImage
                q_img = qimage2ndarray.array2qimage(img_crop)

                # Set the QImage in QLabel
                pixmap = QtGui.QPixmap.fromImage(q_img)
                self.img_display.setPixmap(pixmap)
                if self.roi_xmax > 0 or self.roi_ymax > 0:
                    cv2.destroyAllWindows()
            except:
                cv2.destroyAllWindows()

    def acquire_image(self):
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        try:
            if cam_list.GetSize() == 0:
                QMessageBox.critical(self, "Error", "No cameras found")
                return False
            else:
                cam = cam_list.GetByIndex(0)
                cam.Init()
                cam.BeginAcquisition()
                image_result = cam.GetNextImage()
                self.image = image_result.GetNDArray()
                image_result.Release()
                cam.EndAcquisition()
                cam.DeInit()
                del cam
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return False
        cam_list.Clear()
        system.ReleaseInstance()
        return True 


    def recording(self):
        if not self.is_plotting:
            QMessageBox.critical(self,
            "Recording Cannot Start",
            "Please begin plotting before recording."
            )
        else:
            # if len(deque_record) == 0:
            #     deque_record.append(1)
            self.rec_worker = RecordingWorker(self.deque_recording, self.roi, images_folder_path= self.images_folder_path)
            self.rec_worker.is_running = True
            self.rec_worker.start() 
            

    def plotting(self):
        if not self.is_experiment_initialized:
            QMessageBox.critical(self,
            "Plotting Cannot Start",
            "Please initialize the new experiment first."
            )
            return
        self.acq_worker = FLIRAcquisitionWorker(self.deque_recording, self.deque_plotting )
        self.acq_worker.is_running = True        
        self.acq_worker.start()

        self.plot_timer = QtCore.QTimer()
        self.plot_timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.plot_timer.timeout.connect(self.update_plot)
        self.plot_timer.start(10)
        self.is_plotting = True


    def update_plot(self):
        # Only update if deques are not empty
        if self.deque_plotting:
            t, img = self.deque_plotting.popleft()
            if self.iterator == 0:
                self.t0 = time.perf_counter()
            t = t - self.t0
            img = img[self.roi.xmin:self.roi.xmax, self.roi.ymin:self.roi.ymax]
            if self.iterator % 3 == 0:
                self.deque_timesteps1.append(t)
                self.deque_sequence1.append(np.mean(img))
                mu, std = np.average(self.deque_sequence1), np.std(self.deque_sequence1)
                if std > 0:
                    sequence = (self.deque_sequence1 - mu )/ std
                    self.plot_chn1.plotItem.clear()
                    self.plot_chn1.plotItem.plot(
                        self.deque_timesteps1,
                        sequence,
                        pen=self.pen1,
                    )
            elif self.iterator % 3 == 1:
                self.deque_timesteps2.append(t)
                self.deque_sequence2.append(np.mean(img))
                mu, std = np.average(self.deque_sequence2), np.std(self.deque_sequence2)
                if std > 0:
                    sequence = (self.deque_sequence2 - mu )/ std
                    self.plot_chn2.plotItem.clear()
                    self.plot_chn2.plotItem.plot(
                        self.deque_timesteps2,
                        sequence,
                        pen=self.pen2,
                    )
            else: 
                self.deque_timesteps3.append(t)
                self.deque_sequence3.append(np.mean(img))
                mu, std = np.average(self.deque_sequence3), np.std(self.deque_sequence3)
                if std > 0:
                    sequence = (self.deque_sequence3 - mu )/ std
                    self.plot_chn3.plotItem.clear()
                    self.plot_chn3.plotItem.plot(
                        self.deque_timesteps3,
                        sequence,
                        pen=self.pen3,
                    )
            self.iterator +=1
            # if self.iterator > 1 and self.iterator % 3 == 0:
            #     sequence = (self.deque_sequence1 - self.deque_sequence2)/self.deque_sequence2
            #     self.plot_final.plotItem.clear()
            #     self.plot_final.plotItem.plot(
            #         self.deque_timesteps1,
            #         sequence,
            #         pen=self.pen4,
            #     )



    def stop(self):
        if self.plot_timer:
            self.plot_timer.stop()
        self.is_plotting = False
        # self.acq_worker.quit()
        df_data = pd.DataFrame({'chn1_time':self.deque_timesteps1, 'chn1_avg_intensity':self.deque_sequence1,'chn2_time':self.deque_timesteps2, 'chn2_avg_intensity':self.deque_sequence2,'chn3_time': self.deque_timesteps3,'chn3_avg_intensity':self.deque_sequence3})
        df_data.to_csv(self.experiment_data_path)
        time.sleep(3)
        if self.rec_worker:
            self.rec_worker.is_running = False  
            time.sleep(1) 
            self.rec_worker.quit() 
        if self.acq_worker:    
            self.acq_worker.is_running = False
            time.sleep(1) 
            self.acq_worker.quit()
        # if len(deque_record) > 0:
        #     _ = deque_record.popleft()
        # if len(deque_acq) > 0:
        #     _ = deque_acq.popleft()
        
        self.close()
        # self.deque_sequence1




    # def signal_identify(self, s1, s2, s3, t1, t2, t3):
    #     # Calculate the mean values of s1, s2, and s3
    #     mean_values = [sum(l) / len(l) for l in [s1, s2, s3] if len(l)>0]

    #     # Combine the lists using zip
    #     combined_data = list(zip(mean_values, [s1, s2, s3], [t1, t2, t3]))

    #     # Sort the combined data based on the mean values
    #     sorted_data = sorted(combined_data, key=lambda x: x[0])

    #     # Separate the sorted data into individual lists
    #     sorted_mean_values, sorted_sequences, sorted_times = zip(*sorted_data)
    #     return sorted_sequences, sorted_times

    # def update_plot(self):        
    #     if img_plot_deque:
    #         t, img = img_plot_deque.popleft()
    #         if self.iterator == 0:
    #             self.t0 = time.perf_counter()
    #         t = t - self.t0
    #         img = img[self.roi.xmin:self.roi.xmax, self.roi.ymin:self.roi.ymax]
    #         if self.iterator % 2 == 0:
    #             self.deque_plot_timestamp_405.append(t)
    #             self.deque_plot_405.append(np.sum(img))            
    #             self.current_405 = np.sum(img)
    #             mu, std = np.average(self.deque_plot_405), np.std(self.deque_plot_405)
    #             if std > 0:
    #                 sequence = (self.deque_plot_405 - mu )/ std
    #                 self.plot_chn1.plotItem.clear()
    #                 self.plot_chn1.plotItem.plot(
    #                     self.deque_plot_timestamp_405,
    #                     sequence,
    #                     pen=self.pen_405,
    #                 )
    #         else:
    #             self.deque_plot_timestamp_470.append(t)
    #             self.deque_plot_470.append(np.sum(img))                
    #             self.current_470 = np.sum(img)
    #             if self.current_405!=0:                    
    #                 self.deque_plot_diff.append((self.current_470-self.current_405)/self.current_405)
    #             else:
    #                 self.deque_plot_diff.append(0)
    #             mu, std = np.average(self.deque_plot_470), np.std(self.deque_plot_470)
    #             if std > 0:
    #                 sequence = (self.deque_plot_470 - mu )/ std
    #                 self.plot_chn2.plotItem.clear()
    #                 self.plot_chn2.plotItem.plot(
    #                     self.deque_plot_timestamp_470,
    #                     sequence,
    #                     pen=self.pen_470,
    #                 )              
    #             self.plot_final.plotItem.clear()
    #             self.plot_final.plotItem.plot(
    #                 self.deque_plot_timestamp_405,
    #                 self.deque_plot_diff,
    #                 pen=self.pen_filtered_signal,
    #             )
    #         # else: 
    #         #     self.deque_plot_timestamp_590.append(t)
    #         #     self.deque_plot_590.append(np.sum(img))
    #         #     mu, std = np.average(self.deque_plot_590), np.std(self.deque_plot_590)
    #         #     if std > 0:
    #         #         sequence = (self.deque_plot_590 - mu )/ std
    #         #         self.plot_chn3.plotItem.clear()
    #         #         self.plot_chn3.plotItem.plot(
    #         #             self.deque_plot_timestamp_590,
    #         #             sequence,
    #         #             pen=self.pen_590,
    #         #         )
    #         self.iterator +=1
    #         # if self.iterator > 1 and self.iterator % 3 == 0:                
    #         #     self.plot_final.plotItem.clear()
    #         #     self.plot_final.plotItem.plot(
    #         #         self.deque_plot_timestamp_405,
    #         #         sequence,
    #         #         pen=self.pen_filtered_signal,
    #         #     )


    # def new(self):
    #     user_folder = QFileDialog.getExistingDirectory(
    #         self, "Open a folder:", os.path.expanduser("~")
    #     )
    #     self.path = user_folder
    #     if self.path:
    #         while len(os.listdir(self.path)) > 0:
    #             QMessageBox.critical(
    #                 self,
    #                 "Invalid Folder Selection",
    #                 "Please select an empty folder",
    #             )
    #             self.new()
    #         if self.path != "" and os.name == "nt":
    #             self.path = PureWindowsPath(self.path)
    #         if self.path != "":
    #             self.img_path = Path(self.path) / "Images"
    #             os.mkdir(self.img_path)
    #             csv_data_name = (
    #                 "ExperimentData_" + str(datetime.date.today()) + ".csv"
    #             )
    #             global rec_csv_data_path
    #             rec_csv_data_path = Path(self.path) / csv_data_name
    #             self.csv_data_path = Path(self.path) / csv_data_name
    #             with open(self.csv_data_path, "w") as file:
    #                 writer = csv.writer(file)
    #                 header = [
    #                     "Timestamp",
    #                     "Sum Fluoresence (405nm)",
    #                     "Sum Fluoresence (470nm)",
    #                     "Sum Fluoresence (590nm)"
    #                 ]
    #                 writer.writerow(header)
    #             csv_info_name = (
    #                 "ExperimentInfo_" + str(datetime.date.today()) + ".csv"
    #             )
    #             self.csv_info_path = Path(self.path) / csv_info_name
    #             with open(self.csv_info_path, "w") as file:
    #                 writer = csv.writer(file)
    #                 header = [
    #                     "Experiment Date and Time",
    #                     "Recording Start Time",
    #                     "Recording End Time",
    #                     "Sampling Rate",
    #                     "Exposure",
    #                     "ROI_XMIN",
    #                     "ROI_XMAX",
    #                     "ROI_YMIN",
    #                     "ROI_YMAX",
    #                     "ROI_XRANGE",
    #                     "ROI_YRANGE",
    #                 ]
    #                 writer.writerow(header)
    #             self.path_selected = True

    # def set_parameters(self):
    #     # Open separate window for choosing image parameters
    #     # self.window = QMainWindow()
    #     self.ui = Settings()
    #     # self.window.show()

    # def plot(self):
    #     try: 
    #         global roi_xmin, roi_xmax, roi_ymin, roi_ymax
    #         roi_xmin,roi_xmax,roi_ymin,roi_ymax = self.roi.xmin,self.roi.xmax,self.roi.ymin,self.roi.ymax
    #         # print(roi_xmin,roi_xmax,roi_ymin,roi_ymax)
    #     except:
    #         QMessageBox.critical(self,
    #         "Plotting Cannot Start",
    #         "Please select parameters before plotting."
    #         )
    #         return
    #     if len(acq_deque) == 0:
    #             acq_deque.append(1)
    #     self.acq_worker = FLIRAcquisitionWorker()
    #     self.acq_worker.start()

    #     self.plot_timer = QtCore.QTimer()
    #     self.plot_timer.setTimerType(QtCore.Qt.PreciseTimer)
    #     self.plot_timer.timeout.connect(self.update_plot)
    #     self.plot_timer.start(10)

    #     self.is_plotting = True

    # def record(self):
    #     if not self.is_plotting:
    #         QMessageBox.critical(self,
    #         "Recording Cannot Start",
    #         "Please begin plotting before recording."
    #         )
    #     else:
    #         if len(record_deque) == 0:
    #             record_deque.append(1)
    #         self.rec_worker = RecordingWorker(images_folder_path= self.images_folder_path)
    #         self.rec_worker.start() 
            
            
                
    # def stop(self):
    #     self.plot_timer.stop()
    #     self.is_plotting = False
    #     self.acq_worker.quit()
    #     time.sleep(1)
    #     if len(record_deque) > 0:
    #         _ = record_deque.popleft()
    #     if len(acq_deque) > 0:
    #         _ = acq_deque.popleft()
    #     time.sleep(3)
    #     self.acq_worker.quit()

    
# class RecordingWorker(QtCore.QThread):
#     def __init__(self, images_folder_path:str, parent=None):
#         self.images_folder_path = images_folder_path
#         super().__init__(parent)

#     def run(self):
#         while len(record_deque) > 0:
#             if len(img_deque) > 0:
#                 img_list = img_deque.popleft()
#                 if len(record_deque) > 0:
#                     # Make sure this folder exists, otherwise it will result in an error
#                     filename = os.path.join(self.images_folder_path, f"img_{img_list[0]}.jpg")
#                     # filename = 'images/img_%s.jpg' % (img_list[0])
#                     # Crop Roi
#                     np_img = img_list[1]
#                     crop_img = np_img[roi_xmin:roi_xmax, roi_ymin:roi_ymax]
#                     img = Image.fromarray(crop_img)
#                     # Save image
#                     img.save(filename)
#                     # print('Image saved at %s\n' % filename)
#             time.sleep(0.01)



# class FLIRAcquisitionWorker(QtCore.QThread):
#     def run(self):
#         self.acq_main()
    
#     def configure_trigger(self, cam):
#         result = True

#         print('*** CONFIGURING HARDWARE TRIGGER ***\n')
#         try:
#             # The trigger must be disabled in order to configure the source
#             nodemap = cam.GetNodeMap()
#             node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
#             if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
#                 print('Unable to disable trigger mode (node retrieval). Aborting...')
#                 return False

#             node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
#             if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
#                 print('Unable to disable trigger mode (enum entry retrieval). Aborting...')
#                 return False

#             node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())

#             print('Trigger mode disabled...')
            
#             # Set TriggerSelector to FrameStart
#             node_trigger_selector= PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSelector'))
#             if not PySpin.IsAvailable(node_trigger_selector) or not PySpin.IsWritable(node_trigger_selector):
#                 print('Unable to get trigger selector (node retrieval). Aborting...')
#                 return False

#             node_trigger_selector_framestart = node_trigger_selector.GetEntryByName('FrameStart')
#             if not PySpin.IsAvailable(node_trigger_selector_framestart) or not PySpin.IsReadable(
#                     node_trigger_selector_framestart):
#                 print('Unable to set trigger selector (enum entry retrieval). Aborting...')
#                 return False
#             node_trigger_selector.SetIntValue(node_trigger_selector_framestart.GetValue())
            
#             print('Trigger selector set to frame start...')

#             # Select trigger source
#             node_trigger_source = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSource'))
#             if not PySpin.IsAvailable(node_trigger_source) or not PySpin.IsWritable(node_trigger_source):
#                 print('Unable to get trigger source (node retrieval). Aborting...')
#                 return False

#             # Set trigger source to hardware
#             node_trigger_source_hardware = node_trigger_source.GetEntryByName('Line0')
#             if not PySpin.IsAvailable(node_trigger_source_hardware) or not PySpin.IsReadable(
#                     node_trigger_source_hardware):
#                 print('Unable to set trigger source (enum entry retrieval). Aborting...')
#                 return False
#             node_trigger_source.SetIntValue(node_trigger_source_hardware.GetValue())
#             print('Trigger source set to hardware...')

#             # Turn trigger mode on
#             node_trigger_mode_on = node_trigger_mode.GetEntryByName('On')
#             if not PySpin.IsAvailable(node_trigger_mode_on) or not PySpin.IsReadable(node_trigger_mode_on):
#                 print('Unable to enable trigger mode (enum entry retrieval). Aborting...')
#                 return False

#             node_trigger_mode.SetIntValue(node_trigger_mode_on.GetValue())
#             print('Trigger mode turned back on...')

#         except PySpin.SpinnakerException as ex:
#             print('Error: %s' % ex)
#             return False

#         return result

    
#     def configure_exposure(self, cam):
#         print('*** CONFIGURING EXPOSURE ***\n')

#         try:
#             result = True

#             # Turn off automatic exposure mode

#             if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
#                 print('Unable to disable automatic exposure. Aborting...')
#                 return False

#             cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
#             print('Automatic exposure disabled...')

#             # Set exposure time manually; exposure time recorded in microseconds

#             if cam.ExposureTime.GetAccessMode() != PySpin.RW:
#                 print('Unable to set exposure time. Aborting...')
#                 return False

#             # Ensure desired exposure time does not exceed the maximum this is in us so 50 ms
#             exposure_time_to_set = 30000.0
#             exposure_time_to_set = min(cam.ExposureTime.GetMax(), exposure_time_to_set)
#             cam.ExposureTime.SetValue(exposure_time_to_set)
#             print('Shutter time set to %s us...\n' % exposure_time_to_set)

#         except PySpin.SpinnakerException as ex:
#             print('Error: %s' % ex)
#             result = False
#         return result
#     def acquire_images(self, cam, nodemap, nodemap_tldevice):

#         print('*** IMAGE ACQUISITION ***\n')
#         try:
#             result = True

#             # Set acquisition mode to continuous
#             node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
#             if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
#                 print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
#                 return False

#             # Retrieve entry node from enumeration node
#             node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
#             if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
#                     node_acquisition_mode_continuous):
#                 print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
#                 return False

#             # Retrieve integer value from entry node
#             acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

#             # Set integer value from entry node as new value of enumeration node
#             node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

#             print('Acquisition mode set to continuous...')

#             #  Begin acquiring images
#             cam.BeginAcquisition()

#             print('Acquiring images...')

#             #  Retrieve device serial number for filename
#             device_serial_number = ''
#             node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
#             if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
#                 device_serial_number = node_device_serial_number.GetValue()
#                 print('Device serial number retrieved as %s...' % device_serial_number)

#             # Retrieve, convert, and save images
#             i = 0
#             with nidaqmx.Task() as ctr_task:
#                 # Trigger for the camera, with an offset of 12.5 milliseconds from the LEDs
#                 #ctr_task.co_channels.add_co_pulse_chan_freq("Dev1/ctr0", freq=10, duty_cycle=0.5, initial_delay=0.025)
#                 # Trigger for BOTH LEDs, 470nm is directly connected, 405nm indirectly using a NOT gate
#                 #ctr_task.co_channels.add_co_pulse_chan_freq("Dev1/ctr1", freq=10, duty_cycle=0.5)
#                 # Run the task for an infinite amount of time until explicitly stopped
#                 # ctr_task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS)
#                 # Start triggering
#                 #ctr_task.start()
#                 while len(acq_deque) > 0:
#                     #  Retrieve next received image
#                     image_result = cam.GetNextImage()

#                     #  Ensure image completion
#                     if image_result.IsIncomplete():
#                         print('Image incomplete with image status %d ...' % image_result.GetImageStatus())

#                     else:

#                         # print('Grabbed Image %d' % (i))

#                         #  Convert image to mono 8
#                         img = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)

#                         # Create a unique filename
#                         t_file = datetime.datetime.now().strftime('%y-%m-%d_%H-%M-%S-%f')
#                         t_plot = time.perf_counter()
                
#                         """
#                         # Make sure this folder exists, otherwise it will result in an error
#                         filename = 'images/img_%s.jpg' % (t_file)
#                         # Save image
#                         img.Save(filename)
#                         print('Image saved at %s\n' % filename)
#                         """
                        
#                         np_img = np.array(img.GetData(), dtype="uint8").reshape((img.GetHeight(), img.GetWidth()))

#                         # Store timestamp and image in global queues for other functions to manipulate
#                         img_deque.append([t_file, np_img])
#                         img_plot_deque.append([t_plot, np_img])

#                         #  Release image
#                         image_result.Release()
#                         # i += 1                
#                 # ctr_task.stop()
#             cam.EndAcquisition()

#         except PySpin.SpinnakerException as ex:
#             print('Error: %s' % ex)
#             return False

#         return result


#     def reset_trigger(self, nodemap):
#         try:
#             result = True
#             node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
#             if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
#                 print('Unable to disable trigger mode (node retrieval). Aborting...')
#                 return False

#             node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
#             if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
#                 print('Unable to disable trigger mode (enum entry retrieval). Aborting...')
#                 return False

#             node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())

#             print('Trigger mode disabled...')

#         except PySpin.SpinnakerException as ex:
#             print('Error: %s' % ex)
#             result = False

#         return result
    
#     def reset_exposure(self, cam):
#         # Return the camera to a normal state by re-enabling automatic exposure.
#         try:
#             result = True
#             if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
#                 print('Unable to enable automatic exposure (node retrieval). Non-fatal error...')
#                 return False

#             cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)

#             print('Automatic exposure enabled...')

#         except PySpin.SpinnakerException as ex:
#             print('Error: %s' % ex)
#             result = False

#         return result



#     def run_single_camera(self, cam):
#         try:
#             result = True
#             err = False

#             # Retrieve TL device nodemap and print device information
#             nodemap_tldevice = cam.GetTLDeviceNodeMap()

#             # Initialize camera
#             cam.Init()

#             # Retrieve GenICam nodemap
#             nodemap = cam.GetNodeMap()

#             # Configure trigger
#             if self.configure_trigger(cam) is False:
#                 return False

#             # Configure exposure
#             if self.configure_exposure(cam) is False:
#                 return False

#             # Acquire images
#             result &= self.acquire_images(cam, nodemap, nodemap_tldevice)

#             # Reset trigger
#             result &= self.reset_trigger(nodemap)

#             # Reset exposure
#             result &= self.reset_exposure(cam)
            
#             # Deinitialize camera
#             cam.DeInit()

#         except PySpin.SpinnakerException as ex:
#             print('Error: %s' % ex)
#             result = False

#         return result


#     def acq_main(self):
#         result = True

#         # Retrieve singleton reference to system object
#         system = PySpin.System.GetInstance()

#         # Retrieve list of cameras from the system
#         cam_list = system.GetCameras()

#         num_cameras = cam_list.GetSize()

#         # Finish if there are no cameras
#         if num_cameras == 0:
#             # Clear camera list before releasing system
#             cam_list.Clear()

#             # Release system instance
#             system.ReleaseInstance()

#             print('Not enough cameras!')
#             input('Done! Press Enter to exit...')
#             return False

#         # Run each camera
#         for i, cam in enumerate(cam_list):

#             print('Running camera %d...' % i)
#             result &= self.run_single_camera(cam)
#             print('Camera %d complete... \n' % i)

#         # Release reference to camera
#         del cam

#         # Clear camera list before releasing system
#         cam_list.Clear()

#         # Release system instance
#         system.ReleaseInstance()

#         print('Done! Exiting program now.')
#         return result


if __name__ == "__main__":
    app = QApplication(sys.argv)
    UIWindow = Main()
    app.exec_()