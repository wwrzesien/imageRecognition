import numpy as np
import cv2
import random
from moments import Part

BLUE_MIN = [110, 38, 66]
BLUE_MAX = [145, 255, 160]
RED_MIN = [0, 125, 153]
RED_MAX = [7, 255, 255]
ORANGE_MIN = [10, 170, 115]
ORANGE_MAX = [18, 243, 180]

# in image: row -> y, col -> x


class Recognizer:
    """Image recognition handler."""
    def __init__(self, image, filename):
        self.image = np.copy(image)
        self.filename = filename

        self.fuzzy_image = None
        self.hsv_image = None
        self.thresh_image = None
        self.segmen_image = None
        self.recog_image = None

        self.rows = image.shape[0]
        self.cols = image.shape[1]
        self.parts = []  # Fed, E, x

    def recognize(self):
        """Perform image recognition."""
        norm = 10
        # Lowpass filtering
        conv = [
                [1/norm, 1/norm, 1/norm],
                [1/norm, 2/norm, 1/norm],
                [1/norm, 1/norm, 1/norm]
            ]

        self.convolution(conv)
        cv2.imwrite("results/convolution/" + self.filename, self.fuzzy_image)

        # # Convert BGR to HSV
        self.hsv_image = cv2.cvtColor(self.fuzzy_image, cv2.COLOR_BGR2HSV)

        self.thresholding()
        cv2.imwrite("results/thresholding/" + self.filename, self.thresh_image)

        self.segmentation()
        cv2.imwrite("results/segmentation/" + self.filename, self.segmen_image)

        self.calculate_moments()
        self.recognition()

        cv2.imshow('FedEx', self.image)
        cv2.imwrite("results/" + self.filename, self.image)

    def thresholding(self):
        """Create black-white image."""
        self.thresh_image = np.copy(self.image)

        for row in range(self.rows):
            for col in range(self.cols):
                if (self.detect_blue(self.hsv_image[row, col])) or (self.detect_red(self.hsv_image[row, col]) or (self.detect_orange(self.hsv_image[row, col]))):
                    self.thresh_image[row, col] = [255, 255, 255]
                else:
                    self.thresh_image[row, col] = [0, 0, 0]

    def segmentation(self):
        """Perform segmentation."""
        self.segmen_image = np.copy(self.thresh_image)
        i = 0
        for row in range(self.rows):
            for col in range(self.cols):
                if self.segmen_image[row, col, 0] == 255 and self.segmen_image[row, col, 1] == 255 and self.segmen_image[row, col, 2] == 255:
                    color = self.get_color(i)
                    self.parts.append(Part(color))
                    self.flood_fill((row, col), color)
                    i += 1
        self.remove_small_parts()
        print(len(self.parts))

    def calculate_moments(self):
        """Calculate moments for parts."""
        for part in self.parts:
            part.count_moments()
            print("Color, NM1, NM2, NM4, NM7")
            print(part.color, part.NM1, part.NM2, part.NM4, part.NM7)
            print(len(part.word_index))

    def recognition(self):
        """Perform recognition."""
        self.recog_image = np.copy(self.segmen_image)
        Fed = []
        E = []
        x = []
        start_line = 0
        end_line = 0

        Fed_line = {
            "min": [],
            "max": [],
        }
        x_line = {
            "min": [],
            "max": [],
        }

        # Detect part
        for part in self.parts:
            if self.is_Fed(part):
                Fed.append(part)
            elif self.is_E(part):
                E.append(part)
            elif self.is_x(part):
                x.append(part)
            else:
                for pixel in part.word_index:
                    self.recog_image[pixel[0], pixel[1], 0] = 0
                    self.recog_image[pixel[0], pixel[1], 1] = 0
                    self.recog_image[pixel[0], pixel[1], 2] = 0

        # Find Fed's egdes
        for part in Fed:
            row_min = np.copy(self.rows)
            col_min = np.copy(self.cols)
            row_max = col_max = 0
            for pixel in part.word_index:
                if pixel[0] > row_max:
                    row_max = np.copy(pixel[0])
                if pixel[0] < row_min:
                    row_min = np.copy(pixel[0])
                if pixel[1] > col_max:
                    col_max = np.copy(pixel[1])
                if pixel[1] < col_min:
                    col_min = np.copy(pixel[1])
            Fed_line["min"].append((row_min, col_min))
            Fed_line["max"].append((row_max, col_max))

        # Find x's egdes
        for part in x:
            row_min = np.copy(self.rows)
            col_min = np.copy(self.cols)
            row_max = col_max = 0
            for pixel in part.word_index:
                if pixel[0] > row_max:
                    row_max = np.copy(pixel[0])
                if pixel[0] < row_min:
                    row_min = np.copy(pixel[0])
                if pixel[1] > col_max:
                    col_max = np.copy(pixel[1])
                if pixel[1] < col_min:
                    col_min = np.copy(pixel[1])
            x_line["min"].append((row_min, col_min))
            x_line["max"].append((row_max, col_max))

        # Find word's egdes
        for i, value in enumerate(Fed_line["min"]):
            row_min = x_line["min"][i][0] if (Fed_line["min"][i][0] > x_line["min"][i][0]) else Fed_line["min"][i][0]
            row_max = Fed_line["max"][i][0] if (Fed_line["max"][i][0] > x_line["max"][i][0]) else x_line["max"][i][0]
            col_min = Fed_line["min"][i][1]
            col_max = x_line["max"][i][1]
            start_line = (col_min, row_min)
            end_line = (col_max, row_max)
            cv2.rectangle(self.image, start_line, end_line, (0, 100, 0), 1)

    def flood_fill(self, position, part_color):
        """Divide image into separate parts."""
        position_queue = []
        position_queue.append(position)

        while position_queue:
            current = position_queue[0]
            position_queue.pop(0)

            self.segmen_image[current[0], current[1], 0] = part_color[0]
            self.segmen_image[current[0], current[1], 1] = part_color[1]
            self.segmen_image[current[0], current[1], 2] = part_color[2]

            self.parts[-1].word_index.append(current)

            left = (current[0], current[1]-1)
            right = (current[0], current[1]+1)
            top = (current[0]-1, current[1])
            bottom = (current[0]+1, current[1])

            if left[1] >= 0 and self.segmen_image[left[0], left[1], 0] == 255:
                if self.segmen_image[left[0], left[1], 1] == 255:
                    if self.segmen_image[left[0], left[1], 2] == 255:
                        if left not in position_queue:
                            position_queue.append(left)

            if right[1] < self.cols and self.segmen_image[right[0], right[1], 0] == 255:
                if self.segmen_image[right[0], right[1], 1] == 255:
                    if self.segmen_image[right[0], right[1], 2] == 255:
                        if right not in position_queue:
                            position_queue.append(right)

            if top[0] >= 0 and self.segmen_image[top[0], top[1], 0] == 255:
                if self.segmen_image[top[0], top[1], 1] == 255:
                    if self.segmen_image[top[0], top[1], 2] == 255:
                        if top not in position_queue:
                            position_queue.append(top)

            if bottom[0] < self.rows and self.segmen_image[bottom[0], bottom[1], 0] == 255:
                if self.segmen_image[bottom[0], bottom[1], 1] == 255:
                    if self.segmen_image[bottom[0], bottom[1], 2] == 255:
                        if bottom not in position_queue:
                            position_queue.append(bottom)

    def convolution(self, filtr):
        """Perform convolution."""
        def cut(vector):
            for index, value in enumerate(vector):
                if value >= 255:
                    vector[index] = 255
                elif value <= 0:
                    vector[index] = 0
            return vector

        self.fuzzy_image = np.copy(self.image)

        for row in range(1, self.rows-1):
            for col in range(1, self.cols-1):
                tmp = [0, 0, 0]
                for k in range(-1, 2):
                    for l in range(-1, 2):
                        tmp[0] += self.image[row+k, col+l, 0] * filtr[1+k][1+l]
                        tmp[1] += self.image[row+k, col+l, 1] * filtr[1+k][1+l]
                        tmp[2] += self.image[row+k, col+l, 2] * filtr[1+k][1+l]
                self.fuzzy_image[row, col] = cut(tmp)

    def detect_blue(self, pixel):
        """Detect blue color."""
        if (pixel[0] >= BLUE_MIN[0] and pixel[0] <= BLUE_MAX[0]):
            if (pixel[1] >= BLUE_MIN[1] and pixel[1] <= BLUE_MAX[1]):
                if (pixel[2] >= BLUE_MIN[2] and pixel[2] <= BLUE_MAX[2]):
                    return True
        return False

    def detect_red(self, pixel):
        """Detect red color."""
        if (pixel[0] >= RED_MIN[0] and pixel[0] <= RED_MAX[0]):
            if (pixel[1] >= RED_MIN[1] and pixel[1] <= RED_MAX[1]):
                if (pixel[2] >= RED_MIN[2] and pixel[2] <= RED_MAX[2]):
                    return True
        return False

    def detect_orange(self, pixel):
        """Detect orange color."""
        if (pixel[0] >= ORANGE_MIN[0] and pixel[0] <= ORANGE_MAX[0]):
            if (pixel[1] >= ORANGE_MIN[1] and pixel[1] <= ORANGE_MAX[1]):
                if (pixel[2] >= ORANGE_MIN[2] and pixel[2] <= ORANGE_MAX[2]):
                    return True
        return False

    def remove_small_parts(self):
        """Remove parts with area less than 10px."""
        to_remove = []
        for index, part in enumerate(self.parts):
            if len(part.word_index) < 90:
                for pixel in part.word_index:
                    self.segmen_image[pixel[0], pixel[1], 0] = 0
                    self.segmen_image[pixel[0], pixel[1], 1] = 0
                    self.segmen_image[pixel[0], pixel[1], 2] = 0
                to_remove.append(part)

        for part in to_remove:
            self.parts.remove(part)

    def get_color(self, i):
        """Get color for part."""
        color = [
            [255, 0, 0],
            [0, 255, 0],
            [0, 0, 255],
        ]

        for n in range(1000):
            b = random.randint(0, 255)
            g = random.randint(0, 255)
            r = random.randint(0, 255)
            color.append([b, g, r])
        return color[i]

    def is_Fed(self, part):
        """Check whether part is Fed element."""
        if part.NM1 >= 0.30 and part.NM1 <= 0.45:
            if part.NM2 >= 0.015 and part.NM2 <= 0.095:
                if part.NM7 >= 0.018 and part.NM7 <= 0.265:
                    if part.NM4 >= 0.00028 and part.NM4 <= 0.00099:
                        return True
        return False

    def is_E(self, part):
        """Check whether part is E element."""
        if part.NM1 >= 0.28 and part.NM1 <= 0.81:
            if part.NM2 >= 0.028 and part.NM2 <= 0.6:
                if part.NM7 >= 0.012 and part.NM7 <= 0.023:
                    if part.NM4 >= 0.000022 and part.NM4 <= 0.0011:
                        return True
        return False

    def is_x(self, part):
        """Check whether part is x element."""
        if part.NM1 >= 0.23 and part.NM1 <= 0.48:
            if part.NM2 >= 0.000034 and part.NM2 <= 0.162:
                if part.NM7 >= 0.012 and part.NM7 <= 0.021:
                    if part.NM4 >= 0.00000001 and part.NM4 <= 0.000055:
                        return True
        return False
