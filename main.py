import tkinter as tk
from tkinter import filedialog
import cv2
import numpy as np
from PIL import Image, ImageTk


class WatermarkRemover:
    def __init__(self, master):
        self.master = master
        self.master.title('Watermark Remover')

        # 创建界面控件
        self.create_widgets()

        # 初始化变量
        self.img = None
        self.canvas_img = None
        self.mask = None
        self.output = None
        self.origin_width = 0
        self.origin_height = 0
        self.ratio = 1

    def create_widgets(self):
        # 创建菜单栏
        menubar = tk.Menu(self.master)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="打开图片", command=self.open_file)
        filemenu.add_command(label="保存图片", command=self.save_image)
        filemenu.add_separator()
        filemenu.add_command(label="退出", command=self.master.quit)
        menubar.add_cascade(label="文件", menu=filemenu)
        self.master.config(menu=menubar)

        # 创建 Label，用于显示图像和宽高信息
        self.image_label = tk.Label(self.master)
        self.image_label.pack(side=tk.LEFT, padx=10, pady=10)
        self.width_label = tk.Label(self.master, text="宽度：")
        self.width_label.pack(side=tk.TOP, anchor=tk.W, padx=10)
        self.height_label = tk.Label(self.master, text="高度：")
        self.height_label.pack(side=tk.TOP, anchor=tk.W, padx=10)
        self.ratio_label = tk.Label(self.master, text="缩放比例：")
        self.ratio_label.pack(side=tk.TOP, anchor=tk.W, padx=10)

        # 创建 Canvas，用于选择去除水印的区域
        self.canvas = tk.Canvas(self.master, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        # 创建按钮，用于启动去除水印的算法
        self.remove_button = tk.Button(self.master, text="去除水印", command=self.remove_watermark)
        self.remove_button.pack(side=tk.TOP, pady=10)
    
    def open_file(self):
        # 弹出文件对话框，选择要打开的图像文件
        file_path = filedialog.askopenfilename(title="Open Files")
        if file_path:
            # 加载图像
            self.img = cv2.imread(file_path)

            # 将 BGR 图像转换为 RGB 图像
            self.img = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)

            # 将 NumPy 数组转换为 PIL 图像对象
            pil_image = Image.fromarray(self.img)

            # 获取图像的宽高信息
            width, height = pil_image.size
            self.origin_height = height
            self.origin_width = width
            self.ratio = 1
            while(width > 1000 or height > 1000):
                width = int(width / 2)
                height = int(height / 2)
                pil_image = pil_image.resize((width, height), Image.ANTIALIAS)
                # self.img = cv2.resize(self.img, (width, height))
                self.ratio = self.ratio / 2

            # 在 Label 中显示图像和宽高信息
            self.tk_image = ImageTk.PhotoImage(pil_image)
            self.image_label.config(image=self.tk_image)
            self.width_label.config(text=f"宽度：{width}, 原宽度：{self.origin_width}")
            self.height_label.config(text=f"高度：{height}, 原高度：{self.origin_height}")
            self.ratio_label.config(text=f"缩放比例：{self.ratio} (去水印和保存都会以原图大小进行)")

            # 在 Canvas 中显示图像
            self.canvas.delete("all")
            self.tk_canvas_image = ImageTk.PhotoImage(pil_image)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_canvas_image)

            # 初始化变量
            self.mask = np.zeros((self.img.shape[0], self.img.shape[1]), dtype=np.uint8)

    def on_mouse_down(self, event):
        # 记录鼠标按下时的位置
        self.start_x, self.start_y = event.x, event.y

        # 创建新的遮罩图像
        if self.mask is None:
            self.mask = np.zeros((self.img.shape[0], self.img.shape[1]), dtype=np.uint8)

    def on_mouse_move(self, event):
        # 绘制矩形，用于标记去除水印的区域
        self.canvas.delete("rect")
        self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="white", tag="rect")

        # 在遮罩图像上绘制矩形，用于标记去除水印的区域
        # 根据self.ratio，用坐标还原到缩放前的坐标来更改mask区域
        self.mask[int(self.start_y/self.ratio):int(event.y/self.ratio), int(self.start_x/self.ratio):int(event.x/self.ratio)] = 255
        # print(f'debug: mask rect position: ({self.start_x}, {self.start_y}) ({event.x}, {event.y})')

    def on_mouse_up(self, event):
        # 绘制矩形，用于标记去除水印的区域
        self.canvas.delete("rect")
        self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="white", tag="rect")

        # 在遮罩图像上绘制矩形，用于标记去除水印的区域
        self.mask[self.start_y:event.y, self.start_x:event.x] = 255

    def remove_watermark(self):
        if self.mask is not None:
            # 将遮罩图像的数值限制在 [0, 1] 之间
            mask = np.clip(self.mask, 0, 1)

            # 将原始图像转换为 8 位无符号整数的三通道数组
            # print(f'debug: img dtype: {self.img.dtype}')
            # self.tk_image = ImageTk.PhotoImage(Image.fromarray(self.img, mode='RGB'))
            # self.image_label.config(image=self.tk_image)            

            # 将遮罩图像转换为单通道数组
            mask_gray = (mask * 255).astype(np.uint8)

            # 使用 inpaint 方法进行水印去除
            img_result = cv2.inpaint(self.img, mask_gray, 5, cv2.INPAINT_TELEA)

            # 将 NumPy 数组转换为 PIL 图像对象
            pil_image = Image.fromarray(img_result, mode='RGB')

            # 根据self.ratio按缩放比例再展示
            width, height = pil_image.size[0] * self.ratio, pil_image.size[1] * self.ratio
            display_pil_image = pil_image.resize((int(width), int(height)), Image.ANTIALIAS)
            # 在 Label 中显示去除水印后的图像
            self.tk_image = ImageTk.PhotoImage(display_pil_image)
            self.image_label.config(image=self.tk_image)
            self.output = pil_image
            # 更新遮罩图像
            self.mask = None


    def save_image(self):
        # 获取文件保存路径
        file_path = filedialog.asksaveasfilename(defaultextension=".jpg")

        if file_path and self.output:
            # 将 PhotoImage 对象转换为 PIL.Image.Image 对象
            self.output.save(file_path)
        else:
            print('debug: no output image')
           
if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkRemover(root)
    root.mainloop()