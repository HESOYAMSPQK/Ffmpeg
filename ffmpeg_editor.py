"""
FFmpeg Video Editor с предпросмотром в реальном времени
+ Расширенные функции уникализации (Canvas, Audio Pitch, Metadata)
Автор: AI Assistant
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import os
import threading
import tempfile
from PIL import Image, ImageTk
import cv2
import numpy as np
import json
import re
import random
import string
import uuid

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class FFmpegPreviewEditor(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Основные настройки окна
        self.title("🎬 FFmpeg Video Editor + Уникализация")
        self.geometry("1500x950")
        self.minsize(1300, 850)
        
        # Переменные
        self.video_path = None
        self.video_duration = 0
        self.video_fps = 30
        self.video_width = 0
        self.video_height = 0
        self.video_sample_rate = 44100
        self.preview_frame = None
        self.preview_time = 0.0
        self.is_playing = False
        self.play_thread = None
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        
        # Параметры FFmpeg
        self.params = {
            # Цветокоррекция
            "brightness": ctk.DoubleVar(value=0),
            "contrast": ctk.DoubleVar(value=1),
            "saturation": ctk.DoubleVar(value=1),
            "gamma": ctk.DoubleVar(value=1),
            "gamma_r": ctk.DoubleVar(value=1),
            "gamma_g": ctk.DoubleVar(value=1),
            "gamma_b": ctk.DoubleVar(value=1),
            
            # Резкость и размытие
            "sharpen": ctk.DoubleVar(value=0),
            "blur": ctk.DoubleVar(value=0),
            
            # Шумоподавление
            "denoise_strength": ctk.DoubleVar(value=0),
            
            # Виньетка
            "vignette": ctk.DoubleVar(value=0),
            
            # Поворот и отражение
            "rotation": ctk.IntVar(value=0),
            "hflip": ctk.BooleanVar(value=False),
            "vflip": ctk.BooleanVar(value=False),
            
            # Масштабирование
            "scale_width": ctk.StringVar(value=""),
            "scale_height": ctk.StringVar(value=""),
            
            # Обрезка
            "crop_x": ctk.IntVar(value=0),
            "crop_y": ctk.IntVar(value=0),
            "crop_w": ctk.IntVar(value=0),
            "crop_h": ctk.IntVar(value=0),
            
            # Скорость
            "speed": ctk.DoubleVar(value=1.0),
            
            # Цветовые эффекты
            "hue": ctk.DoubleVar(value=0),
            "colorize": ctk.BooleanVar(value=False),
            "negate": ctk.BooleanVar(value=False),
            
            # Дополнительные фильтры
            "eq_preset": ctk.StringVar(value="none"),
            "custom_filter": ctk.StringVar(value=""),
            
            # ========== УНИКАЛИЗАЦИЯ ==========
            # Canvas Effect
            "canvas_enabled": ctk.BooleanVar(value=False),
            "canvas_scale": ctk.DoubleVar(value=0.85),  # 0.7 - 1.0
            "canvas_blur": ctk.DoubleVar(value=25),      # 0 - 50
            "canvas_corner_radius": ctk.DoubleVar(value=20),  # 0 - 50
            "canvas_corner_smooth": ctk.DoubleVar(value=1.0),  # 0.5 - 3.0 (множитель области скругления)
            "canvas_bg_zoom": ctk.DoubleVar(value=1.15),  # 1.0 - 1.3
            "canvas_noise": ctk.DoubleVar(value=0),  # 0 - 30 (интенсивность шума)
            "canvas_vignette": ctk.DoubleVar(value=0.3),  # 0 - 1.0
            
            # Audio Pitch
            "audio_pitch": ctk.DoubleVar(value=1.0),  # 0.95 - 1.05
            "audio_pitch_enabled": ctk.BooleanVar(value=False),
            
            # Metadata
            "clear_metadata": ctk.BooleanVar(value=True),
            "random_metadata": ctk.BooleanVar(value=True),
        }
        
        # Создание интерфейса
        self._create_ui()
        self._bind_params()
        
    def _create_ui(self):
        """Создание основного интерфейса"""
        # Основной контейнер
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Левая панель - превью
        self._create_preview_panel()
        
        # Правая панель - параметры
        self._create_params_panel()
        
        # Нижняя панель - управление
        self._create_control_panel()
        
    def _create_preview_panel(self):
        """Панель предпросмотра"""
        self.preview_panel = ctk.CTkFrame(self.main_container, corner_radius=15)
        self.preview_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Заголовок
        header = ctk.CTkFrame(self.preview_panel, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(
            header, 
            text="📺 Предпросмотр",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")
        
        # Кнопка загрузки видео
        self.load_btn = ctk.CTkButton(
            header,
            text="📂 Загрузить видео",
            command=self.load_video,
            width=150,
            height=35,
            font=ctk.CTkFont(size=14),
            fg_color="#2d5a27",
            hover_color="#3d7a37"
        )
        self.load_btn.pack(side="right")
        
        # Область предпросмотра
        self.preview_container = ctk.CTkFrame(
            self.preview_panel, 
            fg_color="#1a1a2e",
            corner_radius=10
        )
        self.preview_container.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Холст для видео
        self.canvas_frame = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        self.canvas_frame.pack(fill="both", expand=True)
        
        self.preview_label = ctk.CTkLabel(
            self.canvas_frame,
            text="🎬 Загрузите видео для начала работы\n\nПоддерживаемые форматы:\nMP4, AVI, MKV, MOV, WebM, и другие",
            font=ctk.CTkFont(size=16),
            text_color="#666"
        )
        self.preview_label.pack(expand=True)
        
        # Таймлайн
        self.timeline_frame = ctk.CTkFrame(self.preview_panel, fg_color="transparent")
        self.timeline_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.time_label = ctk.CTkLabel(
            self.timeline_frame,
            text="00:00.00 / 00:00.00",
            font=ctk.CTkFont(size=12, family="Consolas")
        )
        self.time_label.pack(side="left")
        
        self.timeline_slider = ctk.CTkSlider(
            self.timeline_frame,
            from_=0,
            to=100,
            command=self._on_timeline_change,
            width=400
        )
        self.timeline_slider.pack(side="left", fill="x", expand=True, padx=10)
        self.timeline_slider.set(0)
        
        # Кнопки воспроизведения
        play_frame = ctk.CTkFrame(self.timeline_frame, fg_color="transparent")
        play_frame.pack(side="right")
        
        self.play_btn = ctk.CTkButton(
            play_frame,
            text="▶",
            width=40,
            height=30,
            command=self.toggle_play,
            font=ctk.CTkFont(size=14)
        )
        self.play_btn.pack(side="left", padx=2)
        
        self.refresh_btn = ctk.CTkButton(
            play_frame,
            text="🔄",
            width=40,
            height=30,
            command=self.refresh_preview,
            font=ctk.CTkFont(size=14)
        )
        self.refresh_btn.pack(side="left", padx=2)
        
    def _create_params_panel(self):
        """Панель параметров"""
        self.params_panel = ctk.CTkFrame(self.main_container, width=480, corner_radius=15)
        self.params_panel.pack(side="right", fill="y")
        self.params_panel.pack_propagate(False)
        
        # Заголовок
        header = ctk.CTkFrame(self.params_panel, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(
            header,
            text="⚙️ Параметры FFmpeg",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")
        
        # Кнопка сброса
        ctk.CTkButton(
            header,
            text="↺ Сброс",
            width=80,
            height=30,
            command=self.reset_params,
            fg_color="#8b0000",
            hover_color="#a52a2a"
        ).pack(side="right")
        
        # Табы с параметрами
        self.tabview = ctk.CTkTabview(self.params_panel, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Вкладки
        self.tabview.add("🎨 Цвет")
        self.tabview.add("🔧 Фильтры")
        self.tabview.add("📐 Геометрия")
        self.tabview.add("⚡ Эффекты")
        self.tabview.add("🎭 Уникализация")  # НОВАЯ ВКЛАДКА
        self.tabview.add("📝 Свой фильтр")
        
        self._create_color_tab()
        self._create_filters_tab()
        self._create_geometry_tab()
        self._create_effects_tab()
        self._create_uniquify_tab()  # НОВАЯ ВКЛАДКА
        self._create_custom_tab()
        
    def _create_slider_row(self, parent, label, var, from_, to, resolution=0.01):
        """Создание строки со слайдером"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        
        label_widget = ctk.CTkLabel(
            frame, 
            text=label, 
            width=130,
            anchor="w",
            font=ctk.CTkFont(size=13)
        )
        label_widget.pack(side="left")
        
        value_label = ctk.CTkLabel(
            frame,
            text=f"{var.get():.2f}",
            width=50,
            font=ctk.CTkFont(size=12, family="Consolas")
        )
        value_label.pack(side="right")
        
        slider = ctk.CTkSlider(
            frame,
            from_=from_,
            to=to,
            variable=var,
            width=170
        )
        slider.pack(side="right", padx=5)
        
        # Обновление значения
        def update_value(*args):
            value_label.configure(text=f"{var.get():.2f}")
        var.trace_add("write", update_value)
        
        return slider
        
    def _create_color_tab(self):
        """Вкладка цветокоррекции"""
        tab = self.tabview.tab("🎨 Цвет")
        
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # EQ фильтры
        ctk.CTkLabel(
            scroll, 
            text="🌈 Основные настройки",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self._create_slider_row(scroll, "Яркость:", self.params["brightness"], -1, 1)
        self._create_slider_row(scroll, "Контраст:", self.params["contrast"], 0, 3)
        self._create_slider_row(scroll, "Насыщенность:", self.params["saturation"], 0, 3)
        self._create_slider_row(scroll, "Гамма:", self.params["gamma"], 0.1, 3)
        
        # Разделитель
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            scroll,
            text="🔴🟢🔵 Гамма по каналам",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self._create_slider_row(scroll, "Гамма R:", self.params["gamma_r"], 0.1, 3)
        self._create_slider_row(scroll, "Гамма G:", self.params["gamma_g"], 0.1, 3)
        self._create_slider_row(scroll, "Гамма B:", self.params["gamma_b"], 0.1, 3)
        
        # Разделитель
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            scroll,
            text="🎭 Тон",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self._create_slider_row(scroll, "Оттенок (Hue):", self.params["hue"], -180, 180, 1)
        
    def _create_filters_tab(self):
        """Вкладка фильтров"""
        tab = self.tabview.tab("🔧 Фильтры")
        
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        ctk.CTkLabel(
            scroll,
            text="✨ Резкость и размытие",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self._create_slider_row(scroll, "Резкость:", self.params["sharpen"], 0, 3)
        self._create_slider_row(scroll, "Размытие:", self.params["blur"], 0, 10)
        
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            scroll,
            text="🔇 Шумоподавление",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self._create_slider_row(scroll, "Сила:", self.params["denoise_strength"], 0, 10)
        
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            scroll,
            text="🌅 Виньетка",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self._create_slider_row(scroll, "Интенсивность:", self.params["vignette"], 0, 1)
        
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        # Пресеты
        ctk.CTkLabel(
            scroll,
            text="📋 Пресеты эквалайзера",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        presets = [
            ("none", "Без пресета"),
            ("vintage", "🎞️ Винтаж"),
            ("cool", "❄️ Холодный"),
            ("warm", "🔥 Тёплый"),
            ("dramatic", "🎭 Драматичный"),
            ("muted", "🌫️ Приглушённый"),
            ("vibrant", "🌈 Яркий"),
        ]
        
        for value, name in presets:
            ctk.CTkRadioButton(
                scroll,
                text=name,
                variable=self.params["eq_preset"],
                value=value,
                font=ctk.CTkFont(size=13)
            ).pack(anchor="w", pady=3)
            
    def _create_geometry_tab(self):
        """Вкладка геометрии"""
        tab = self.tabview.tab("📐 Геометрия")
        
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # Поворот
        ctk.CTkLabel(
            scroll,
            text="🔄 Поворот",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        rotation_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        rotation_frame.pack(fill="x", pady=5)
        
        for angle, text in [(0, "0°"), (90, "90°"), (180, "180°"), (270, "270°")]:
            ctk.CTkRadioButton(
                rotation_frame,
                text=text,
                variable=self.params["rotation"],
                value=angle,
                width=60
            ).pack(side="left", padx=5)
            
        # Отражение
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            scroll,
            text="🪞 Отражение",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        flip_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        flip_frame.pack(fill="x", pady=5)
        
        ctk.CTkCheckBox(
            flip_frame,
            text="По горизонтали",
            variable=self.params["hflip"]
        ).pack(side="left", padx=10)
        
        ctk.CTkCheckBox(
            flip_frame,
            text="По вертикали",
            variable=self.params["vflip"]
        ).pack(side="left", padx=10)
        
        # Масштаб
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            scroll,
            text="📏 Масштабирование",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(
            scroll,
            text="Оставьте пустым для сохранения оригинала.\nИспользуйте -1 для автоматического расчёта.",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        ).pack(anchor="w", pady=(0, 5))
        
        scale_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        scale_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(scale_frame, text="Ширина:", width=60).pack(side="left")
        ctk.CTkEntry(
            scale_frame,
            textvariable=self.params["scale_width"],
            width=80,
            placeholder_text="авто"
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(scale_frame, text="Высота:", width=60).pack(side="left", padx=(10, 0))
        ctk.CTkEntry(
            scale_frame,
            textvariable=self.params["scale_height"],
            width=80,
            placeholder_text="авто"
        ).pack(side="left", padx=5)
        
        # Быстрые пресеты масштаба
        ctk.CTkLabel(
            scroll,
            text="Быстрые пресеты:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", pady=(10, 5))
        
        presets_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        presets_frame.pack(fill="x")
        
        scale_presets = [
            ("1920x1080", "1080p"),
            ("1280x720", "720p"),
            ("640x480", "480p"),
            ("3840x2160", "4K"),
        ]
        
        for res, name in scale_presets:
            def set_scale(r=res):
                w, h = r.split("x")
                self.params["scale_width"].set(w)
                self.params["scale_height"].set(h)
                self.refresh_preview()
                
            ctk.CTkButton(
                presets_frame,
                text=name,
                width=60,
                height=25,
                command=set_scale,
                fg_color="#444",
                hover_color="#555"
            ).pack(side="left", padx=3)
            
        # Обрезка
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            scroll,
            text="✂️ Обрезка (Crop)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        crop_frame1 = ctk.CTkFrame(scroll, fg_color="transparent")
        crop_frame1.pack(fill="x", pady=5)
        
        ctk.CTkLabel(crop_frame1, text="X:", width=30).pack(side="left")
        ctk.CTkEntry(crop_frame1, textvariable=self.params["crop_x"], width=60).pack(side="left", padx=5)
        ctk.CTkLabel(crop_frame1, text="Y:", width=30).pack(side="left")
        ctk.CTkEntry(crop_frame1, textvariable=self.params["crop_y"], width=60).pack(side="left", padx=5)
        
        crop_frame2 = ctk.CTkFrame(scroll, fg_color="transparent")
        crop_frame2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(crop_frame2, text="W:", width=30).pack(side="left")
        ctk.CTkEntry(crop_frame2, textvariable=self.params["crop_w"], width=60).pack(side="left", padx=5)
        ctk.CTkLabel(crop_frame2, text="H:", width=30).pack(side="left")
        ctk.CTkEntry(crop_frame2, textvariable=self.params["crop_h"], width=60).pack(side="left", padx=5)
        
    def _create_effects_tab(self):
        """Вкладка эффектов"""
        tab = self.tabview.tab("⚡ Эффекты")
        
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # Скорость
        ctk.CTkLabel(
            scroll,
            text="⏱️ Скорость воспроизведения",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self._create_slider_row(scroll, "Скорость:", self.params["speed"], 0.25, 4.0)
        
        speed_presets = ctk.CTkFrame(scroll, fg_color="transparent")
        speed_presets.pack(fill="x", pady=5)
        
        for speed, name in [(0.25, "0.25x"), (0.5, "0.5x"), (1.0, "1x"), (2.0, "2x"), (4.0, "4x")]:
            def set_speed(s=speed):
                self.params["speed"].set(s)
                self.refresh_preview()
                
            ctk.CTkButton(
                speed_presets,
                text=name,
                width=50,
                height=25,
                command=set_speed,
                fg_color="#444",
                hover_color="#555"
            ).pack(side="left", padx=3)
        
        # Цветовые эффекты
        ctk.CTkFrame(scroll, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            scroll,
            text="🎨 Цветовые эффекты",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkCheckBox(
            scroll,
            text="🔲 Чёрно-белый (Colorize)",
            variable=self.params["colorize"]
        ).pack(anchor="w", pady=5)
        
        ctk.CTkCheckBox(
            scroll,
            text="🔄 Негатив (Negate)",
            variable=self.params["negate"]
        ).pack(anchor="w", pady=5)
        
    def _create_uniquify_tab(self):
        """Вкладка уникализации - НОВАЯ"""
        tab = self.tabview.tab("🎭 Уникализация")
        
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # ========== CANVAS EFFECT ==========
        ctk.CTkLabel(
            scroll,
            text="🖼️ Canvas Effect (Холст)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#00d4ff"
        ).pack(anchor="w", pady=(0, 5))
        
        ctk.CTkLabel(
            scroll,
            text="Размытый увеличенный фон + уменьшенное видео\nс закруглёнными углами по центру",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        ).pack(anchor="w", pady=(0, 10))
        
        # Чекбокс включения
        ctk.CTkCheckBox(
            scroll,
            text="✅ Включить Canvas Effect",
            variable=self.params["canvas_enabled"],
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00d4ff",
            hover_color="#00a8cc"
        ).pack(anchor="w", pady=5)
        
        # Слайдеры Canvas
        self._create_slider_row(scroll, "Масштаб видео:", self.params["canvas_scale"], 0.7, 0.95)
        self._create_slider_row(scroll, "Размытие фона:", self.params["canvas_blur"], 5, 50)
        self._create_slider_row(scroll, "Радиус углов:", self.params["canvas_corner_radius"], 0, 50)
        self._create_slider_row(scroll, "Область скругл.:", self.params["canvas_corner_smooth"], 0.5, 3.0)
        self._create_slider_row(scroll, "Zoom фона:", self.params["canvas_bg_zoom"], 1.0, 1.3)
        self._create_slider_row(scroll, "Шум (Noise):", self.params["canvas_noise"], 0, 30)
        self._create_slider_row(scroll, "Виньетка Canvas:", self.params["canvas_vignette"], 0, 1)
        
        # Разделитель
        ctk.CTkFrame(scroll, height=2, fg_color="#444").pack(fill="x", pady=15)
        
        # ========== AUDIO PITCH ==========
        ctk.CTkLabel(
            scroll,
            text="🎵 Audio Pitch (Тон аудио)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ff6b6b"
        ).pack(anchor="w", pady=(0, 5))
        
        ctk.CTkLabel(
            scroll,
            text="Изменение высоты тона без изменения скорости.\nНезаметное для уха, но уникализирует аудио.",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        ).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkCheckBox(
            scroll,
            text="✅ Включить изменение Pitch",
            variable=self.params["audio_pitch_enabled"],
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ff6b6b",
            hover_color="#cc5555"
        ).pack(anchor="w", pady=5)
        
        self._create_slider_row(scroll, "Pitch (тон):", self.params["audio_pitch"], 0.95, 1.05)
        
        # Кнопки быстрого выбора
        pitch_presets = ctk.CTkFrame(scroll, fg_color="transparent")
        pitch_presets.pack(fill="x", pady=5)
        
        for pitch, name in [(0.97, "↓ Ниже"), (1.0, "Норма"), (1.03, "↑ Выше")]:
            def set_pitch(p=pitch):
                self.params["audio_pitch"].set(p)
                self.refresh_preview()
                
            ctk.CTkButton(
                pitch_presets,
                text=name,
                width=70,
                height=25,
                command=set_pitch,
                fg_color="#444",
                hover_color="#555"
            ).pack(side="left", padx=3)
        
        # Случайный pitch
        def random_pitch():
            p = random.uniform(0.97, 1.03)
            self.params["audio_pitch"].set(round(p, 3))
            self.params["audio_pitch_enabled"].set(True)
            
        ctk.CTkButton(
            pitch_presets,
            text="🎲 Случайный",
            width=90,
            height=25,
            command=random_pitch,
            fg_color="#ff6b6b",
            hover_color="#cc5555"
        ).pack(side="left", padx=3)
        
        # Разделитель
        ctk.CTkFrame(scroll, height=2, fg_color="#444").pack(fill="x", pady=15)
        
        # ========== METADATA ==========
        ctk.CTkLabel(
            scroll,
            text="📋 Метаданные",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ffd93d"
        ).pack(anchor="w", pady=(0, 5))
        
        ctk.CTkLabel(
            scroll,
            text="Очистка EXIF и добавление случайных метаданных\nдля обхода детекции дубликатов.",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        ).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkCheckBox(
            scroll,
            text="🗑️ Очистить все метаданные",
            variable=self.params["clear_metadata"],
            font=ctk.CTkFont(size=13),
            fg_color="#ffd93d",
            hover_color="#ccae31",
            text_color="#fff"
        ).pack(anchor="w", pady=5)
        
        ctk.CTkCheckBox(
            scroll,
            text="🎲 Добавить случайные метаданные",
            variable=self.params["random_metadata"],
            font=ctk.CTkFont(size=13),
            fg_color="#ffd93d",
            hover_color="#ccae31",
            text_color="#fff"
        ).pack(anchor="w", pady=5)
        
        # Разделитель
        ctk.CTkFrame(scroll, height=2, fg_color="#444").pack(fill="x", pady=15)
        
        # ========== БЫСТРЫЕ ПРЕСЕТЫ УНИКАЛИЗАЦИИ ==========
        ctk.CTkLabel(
            scroll,
            text="⚡ Быстрые пресеты",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        presets_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        presets_frame.pack(fill="x", pady=5)
        
        def preset_light():
            """Лёгкая уникализация"""
            self.params["audio_pitch_enabled"].set(True)
            self.params["audio_pitch"].set(random.uniform(0.98, 1.02))
            self.params["clear_metadata"].set(True)
            self.params["random_metadata"].set(True)
            self.params["canvas_enabled"].set(False)
            self.refresh_preview()
            
        def preset_medium():
            """Средняя уникализация"""
            self.params["audio_pitch_enabled"].set(True)
            self.params["audio_pitch"].set(random.uniform(0.97, 1.03))
            self.params["clear_metadata"].set(True)
            self.params["random_metadata"].set(True)
            self.params["canvas_enabled"].set(True)
            self.params["canvas_scale"].set(0.92)
            self.params["canvas_blur"].set(20)
            self.params["canvas_corner_radius"].set(15)
            self.params["canvas_corner_smooth"].set(1.2)
            self.params["canvas_noise"].set(3)
            self.params["canvas_vignette"].set(0.2)
            self.refresh_preview()
            
        def preset_heavy():
            """Сильная уникализация"""
            self.params["audio_pitch_enabled"].set(True)
            self.params["audio_pitch"].set(random.uniform(0.96, 1.04))
            self.params["clear_metadata"].set(True)
            self.params["random_metadata"].set(True)
            self.params["canvas_enabled"].set(True)
            self.params["canvas_scale"].set(0.85)
            self.params["canvas_blur"].set(30)
            self.params["canvas_corner_radius"].set(25)
            self.params["canvas_corner_smooth"].set(1.5)
            self.params["canvas_bg_zoom"].set(1.2)
            self.params["canvas_noise"].set(8)
            self.params["canvas_vignette"].set(0.4)
            self.params["brightness"].set(random.uniform(-0.05, 0.05))
            self.params["saturation"].set(random.uniform(0.95, 1.05))
            self.refresh_preview()
        
        ctk.CTkButton(
            presets_frame,
            text="🟢 Лёгкая",
            width=90,
            height=30,
            command=preset_light,
            fg_color="#2d5a27",
            hover_color="#3d7a37"
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            presets_frame,
            text="🟡 Средняя",
            width=90,
            height=30,
            command=preset_medium,
            fg_color="#b8860b",
            hover_color="#daa520"
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            presets_frame,
            text="🔴 Сильная",
            width=90,
            height=30,
            command=preset_heavy,
            fg_color="#8b0000",
            hover_color="#a52a2a"
        ).pack(side="left", padx=3)
        
        # Разделитель
        ctk.CTkFrame(scroll, height=2, fg_color="#444").pack(fill="x", pady=15)
        
        # ========== ЭКСПОРТ ПАРАМЕТРОВ ==========
        ctk.CTkLabel(
            scroll,
            text="📤 Экспорт параметров",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 5))
        
        ctk.CTkLabel(
            scroll,
            text="Скопируйте параметры для использования\nв другой программе или скрипте",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        ).pack(anchor="w", pady=(0, 10))
        
        export_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        export_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(
            export_frame,
            text="📋 Копировать как JSON",
            width=140,
            height=32,
            command=self.copy_params_json,
            fg_color="#1e90ff",
            hover_color="#4169e1"
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            export_frame,
            text="🐍 Копировать как Python",
            width=150,
            height=32,
            command=self.copy_params_python,
            fg_color="#306998",
            hover_color="#4b8bbe"
        ).pack(side="left", padx=3)
        
    def _create_custom_tab(self):
        """Вкладка своего фильтра"""
        tab = self.tabview.tab("📝 Свой фильтр")
        
        ctk.CTkLabel(
            tab,
            text="✏️ Свой фильтр FFmpeg",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(
            tab,
            text="Введите произвольный video filter (без -vf).\nНапример: curves=vintage, или boxblur=5:1",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        ).pack(anchor="w", pady=(0, 10))
        
        self.custom_entry = ctk.CTkTextbox(
            tab,
            height=100,
            font=ctk.CTkFont(size=12, family="Consolas")
        )
        self.custom_entry.pack(fill="x", pady=5)
        
        def apply_custom():
            self.params["custom_filter"].set(self.custom_entry.get("1.0", "end-1c"))
            self.refresh_preview()
            
        ctk.CTkButton(
            tab,
            text="▶ Применить фильтр",
            command=apply_custom,
            fg_color="#2d5a27",
            hover_color="#3d7a37"
        ).pack(pady=10)
        
        # Примеры
        ctk.CTkFrame(tab, height=2, fg_color="#333").pack(fill="x", pady=15)
        
        ctk.CTkLabel(
            tab,
            text="📚 Примеры фильтров:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 10))
        
        examples = [
            ("curves=vintage", "Винтаж"),
            ("chromakey=green:0.1:0.2", "Хромакей"),
            ("edgedetect=mode=wires", "Контуры"),
            ("pixelize=16:16", "Пикселизация"),
            ("colorbalance=rs=.3:gs=-.1", "Баланс цвета"),
            ("sobel", "Фильтр Собеля"),
        ]
        
        for filter_str, name in examples:
            def use_example(f=filter_str):
                self.custom_entry.delete("1.0", "end")
                self.custom_entry.insert("1.0", f)
                
            btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
            btn_frame.pack(fill="x", pady=2)
            
            ctk.CTkButton(
                btn_frame,
                text=name,
                width=120,
                height=25,
                command=use_example,
                fg_color="#333",
                hover_color="#444"
            ).pack(side="left")
            
            ctk.CTkLabel(
                btn_frame,
                text=filter_str,
                font=ctk.CTkFont(size=11, family="Consolas"),
                text_color="#888"
            ).pack(side="left", padx=10)
            
    def _create_control_panel(self):
        """Нижняя панель управления"""
        self.control_panel = ctk.CTkFrame(self, height=100, corner_radius=15)
        self.control_panel.pack(fill="x", padx=10, pady=(0, 10))
        
        # Левая часть - FFmpeg команда
        left_frame = ctk.CTkFrame(self.control_panel, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(
            left_frame,
            text="📋 FFmpeg команда:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w")
        
        cmd_frame = ctk.CTkFrame(left_frame, fg_color="#1a1a2e", corner_radius=5)
        cmd_frame.pack(fill="x", pady=5)
        
        self.cmd_label = ctk.CTkLabel(
            cmd_frame,
            text="ffmpeg -i input.mp4 output.mp4",
            font=ctk.CTkFont(size=10, family="Consolas"),
            anchor="w",
            wraplength=650
        )
        self.cmd_label.pack(fill="x", padx=10, pady=5)
        
        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(
            btn_frame,
            text="📋 Копировать команду",
            width=150,
            height=28,
            command=self.copy_command,
            fg_color="#444",
            hover_color="#555"
        ).pack(side="left", padx=2)
        
        # Кнопка предпросмотра видео (2 сек)
        ctk.CTkButton(
            btn_frame,
            text="🎬 Превью 2 сек",
            width=120,
            height=28,
            command=self.preview_video_clip,
            fg_color="#1e90ff",
            hover_color="#4169e1"
        ).pack(side="left", padx=2)
        
        # Правая часть - экспорт
        right_frame = ctk.CTkFrame(self.control_panel, fg_color="transparent")
        right_frame.pack(side="right", padx=15, pady=10)
        
        self.export_btn = ctk.CTkButton(
            right_frame,
            text="💾 Экспорт видео",
            width=150,
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.export_video,
            fg_color="#2d5a27",
            hover_color="#3d7a37"
        )
        self.export_btn.pack()
        
    def _bind_params(self):
        """Привязка обновления превью к изменению параметров"""
        for name, var in self.params.items():
            if isinstance(var, (ctk.DoubleVar, ctk.IntVar, ctk.BooleanVar)):
                var.trace_add("write", lambda *args: self._schedule_refresh())
                
        self._refresh_scheduled = False
        
    def _schedule_refresh(self):
        """Отложенное обновление превью"""
        if not self._refresh_scheduled:
            self._refresh_scheduled = True
            self.after(150, self._do_scheduled_refresh)
            
    def _do_scheduled_refresh(self):
        """Выполнение отложенного обновления"""
        self._refresh_scheduled = False
        self.refresh_preview()
        
    def load_video(self):
        """Загрузка видео файла"""
        filetypes = [
            ("Видео файлы", "*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv *.m4v"),
            ("Все файлы", "*.*")
        ]
        
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.video_path = path
            self._load_video_info()
            self.refresh_preview()
            
    def _load_video_info(self):
        """Получение информации о видео через ffprobe"""
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,duration",
                "-show_entries", "format=duration",
                "-of", "json",
                self.video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            info = json.loads(result.stdout)
            
            stream = info.get("streams", [{}])[0]
            self.video_width = stream.get("width", 1920)
            self.video_height = stream.get("height", 1080)
            
            # FPS
            fps_str = stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                self.video_fps = float(num) / float(den)
            else:
                self.video_fps = float(fps_str)
                
            # Длительность
            self.video_duration = float(info.get("format", {}).get("duration", 
                                        stream.get("duration", 10)))
            
            # Обновить обрезку по умолчанию
            self.params["crop_w"].set(self.video_width)
            self.params["crop_h"].set(self.video_height)
            
            # Получить sample rate аудио
            cmd_audio = [
                self.ffprobe_path,
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=sample_rate",
                "-of", "json",
                self.video_path
            ]
            result_audio = subprocess.run(cmd_audio, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            audio_info = json.loads(result_audio.stdout)
            audio_stream = audio_info.get("streams", [{}])
            if audio_stream:
                self.video_sample_rate = int(audio_stream[0].get("sample_rate", 44100))
            
        except Exception as e:
            print(f"Ошибка получения информации о видео: {e}")
            self.video_duration = 10
            self.video_fps = 30
            self.video_width = 1920
            self.video_height = 1080
            self.video_sample_rate = 44100
            
    def build_filter_chain(self, for_canvas_fg=False, force_build=False):
        """Построение цепочки фильтров FFmpeg
        
        for_canvas_fg=True: строим только цветовые фильтры для наложения поверх Canvas
        force_build=True: строим фильтры даже когда Canvas включен (fallback)
        """
        filters = []
        
        # Если Canvas включен и это НЕ для переднего плана, пропускаем обычные фильтры
        # (они будут применены к композиции)
        # force_build позволяет строить фильтры даже когда Canvas включен
        if self.params["canvas_enabled"].get() and not for_canvas_fg and not force_build:
            return None
        
        # Геометрические фильтры НЕ применяются поверх Canvas (for_canvas_fg=True)
        # Они применяются только к исходному видео
        if not for_canvas_fg:
            # Обрезка (должна быть первой)
            crop_w = self.params["crop_w"].get()
            crop_h = self.params["crop_h"].get()
            crop_x = self.params["crop_x"].get()
            crop_y = self.params["crop_y"].get()
            
            if crop_w > 0 and crop_h > 0:
                if crop_w != self.video_width or crop_h != self.video_height or crop_x != 0 or crop_y != 0:
                    filters.append(f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}")
            
            # Масштабирование (только если Canvas выключен)
            if not self.params["canvas_enabled"].get():
                scale_w = self.params["scale_width"].get().strip()
                scale_h = self.params["scale_height"].get().strip()
                
                if scale_w or scale_h:
                    sw = scale_w if scale_w else "-1"
                    sh = scale_h if scale_h else "-1"
                    filters.append(f"scale={sw}:{sh}")
                
            # Поворот
            rotation = self.params["rotation"].get()
            if rotation == 90:
                filters.append("transpose=1")
            elif rotation == 180:
                filters.append("transpose=1,transpose=1")
            elif rotation == 270:
                filters.append("transpose=2")
                
            # Отражение
            if self.params["hflip"].get():
                filters.append("hflip")
            if self.params["vflip"].get():
                filters.append("vflip")
            
        # Цветокоррекция (eq фильтр)
        eq_parts = []
        
        brightness = self.params["brightness"].get()
        if brightness != 0:
            eq_parts.append(f"brightness={brightness}")
            
        contrast = self.params["contrast"].get()
        if contrast != 1:
            eq_parts.append(f"contrast={contrast}")
            
        saturation = self.params["saturation"].get()
        if saturation != 1:
            eq_parts.append(f"saturation={saturation}")
            
        gamma = self.params["gamma"].get()
        if gamma != 1:
            eq_parts.append(f"gamma={gamma}")
            
        gamma_r = self.params["gamma_r"].get()
        if gamma_r != 1:
            eq_parts.append(f"gamma_r={gamma_r}")
            
        gamma_g = self.params["gamma_g"].get()
        if gamma_g != 1:
            eq_parts.append(f"gamma_g={gamma_g}")
            
        gamma_b = self.params["gamma_b"].get()
        if gamma_b != 1:
            eq_parts.append(f"gamma_b={gamma_b}")
            
        if eq_parts:
            filters.append(f"eq={':'.join(eq_parts)}")
            
        # Тон (hue)
        hue = self.params["hue"].get()
        if hue != 0:
            filters.append(f"hue=h={hue}")
            
        # Резкость
        sharpen = self.params["sharpen"].get()
        if sharpen > 0:
            amount = sharpen
            filters.append(f"unsharp=5:5:{amount}:5:5:{amount}")
            
        # Размытие
        blur = self.params["blur"].get()
        if blur > 0:
            filters.append(f"boxblur={blur}:1")
            
        # Шумоподавление
        denoise = self.params["denoise_strength"].get()
        if denoise > 0:
            filters.append(f"nlmeans={denoise}:7:5:3:3")
            
        # Виньетка (только если Canvas выключен)
        if not self.params["canvas_enabled"].get():
            vignette = self.params["vignette"].get()
            if vignette > 0:
                filters.append(f"vignette=PI/{4/vignette if vignette > 0 else 4}")
            
        # Цветовые эффекты
        if self.params["colorize"].get():
            filters.append("colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3")
            
        if self.params["negate"].get():
            filters.append("negate")
            
        # Пресет эквалайзера
        preset = self.params["eq_preset"].get()
        preset_filters = {
            "vintage": "curves=vintage",
            "cool": "colortemperature=t=9000",
            "warm": "colortemperature=t=4500",
            "dramatic": "eq=contrast=1.3:saturation=1.2:gamma=0.8",
            "muted": "eq=saturation=0.6:contrast=0.9",
            "vibrant": "eq=saturation=1.5:contrast=1.1",
        }
        
        if preset in preset_filters:
            filters.append(preset_filters[preset])
            
        # Скорость
        speed = self.params["speed"].get()
        if speed != 1.0:
            filters.append(f"setpts={1/speed}*PTS")
            
        # Кастомный фильтр
        custom = self.params["custom_filter"].get().strip()
        if custom:
            filters.append(custom)
            
        return ",".join(filters) if filters else None
    
    def build_canvas_filter(self):
        """Построение complex filter для Canvas Effect"""
        if not self.params["canvas_enabled"].get():
            return None
            
        scale = self.params["canvas_scale"].get()
        blur = int(self.params["canvas_blur"].get())
        corner_radius = int(self.params["canvas_corner_radius"].get())
        corner_smooth = self.params["canvas_corner_smooth"].get()  # Множитель области скругления
        bg_zoom = self.params["canvas_bg_zoom"].get()
        noise = int(self.params["canvas_noise"].get())  # Интенсивность шума
        vignette = self.params["canvas_vignette"].get()
        
        # Расчёт размеров
        w = self.video_width
        h = self.video_height
        
        fg_w = int(w * scale)
        fg_h = int(h * scale)
        # Делаем размеры чётными
        fg_w = fg_w if fg_w % 2 == 0 else fg_w - 1
        fg_h = fg_h if fg_h % 2 == 0 else fg_h - 1
        
        bg_w = int(w * bg_zoom)
        bg_h = int(h * bg_zoom)
        bg_w = bg_w if bg_w % 2 == 0 else bg_w - 1
        bg_h = bg_h if bg_h % 2 == 0 else bg_h - 1
        
        # Построение complex filter
        # 1. Сплит на два потока
        # 2. Фон: увеличить + размыть + обрезать до оригинального размера
        # 3. Передний план: уменьшить + закруглить углы
        # 4. Наложить по центру
        # 5. Добавить виньетку и шум
        
        filter_parts = []
        
        # Сплит входа
        filter_parts.append(f"[0:v]split=2[bg][fg]")
        
        # Обработка фона: увеличить, размыть, обрезать до оригинального размера
        filter_parts.append(f"[bg]scale={bg_w}:{bg_h},boxblur={blur}:{blur},crop={w}:{h}[bg_out]")
        
        # Обработка переднего плана с закруглёнными углами
        # corner_smooth увеличивает область скругления (не только радиус, но и "толщину")
        if corner_radius > 0:
            # r - радиус скругления
            # s - область скругления (умножается на радиус для определения зоны)
            r = corner_radius
            s = int(corner_radius * corner_smooth)  # Расширенная область для проверки
            
            # Формула для закругления углов через альфа-канал
            # s определяет зону где происходит проверка (область скругления)
            # r определяет сам радиус окружности внутри этой зоны
            filter_parts.append(
                f"[fg]scale={fg_w}:{fg_h},format=rgba,"
                f"geq="
                f"'r=r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                f"a='if(lt(X,{s})*lt(Y,{s}),if(lte(hypot({s}-X,{s}-Y),{r}),255,0),"
                f"if(gt(X,W-{s})*lt(Y,{s}),if(lte(hypot(X-W+{s},{s}-Y),{r}),255,0),"
                f"if(lt(X,{s})*gt(Y,H-{s}),if(lte(hypot({s}-X,Y-H+{s}),{r}),255,0),"
                f"if(gt(X,W-{s})*gt(Y,H-{s}),if(lte(hypot(X-W+{s},Y-H+{s}),{r}),255,0),"
                f"255))))'"
                f"[fg_rounded]"
            )
        else:
            filter_parts.append(f"[fg]scale={fg_w}:{fg_h},format=rgba[fg_rounded]")
        
        # Наложение по центру
        filter_parts.append(f"[bg_out][fg_rounded]overlay=(W-w)/2:(H-h)/2:format=auto[composed]")
        
        current_label = "[composed]"
        
        # Добавление виньетки поверх композиции (если включена)
        if vignette > 0:
            filter_parts.append(f"{current_label}vignette=PI/{4/vignette if vignette > 0 else 4}[vignette_out]")
            current_label = "[vignette_out]"
        
        # Добавление шума (если включен)
        if noise > 0:
            filter_parts.append(f"{current_label}noise=c0s={noise}:allf=t[noise_out]")
            current_label = "[noise_out]"
            
        # Дополнительные фильтры поверх Canvas
        extra_filters = self.build_filter_chain(for_canvas_fg=True)
        if extra_filters:
            filter_parts.append(f"{current_label}{extra_filters}[out]")
            current_label = "[out]"
        
        return ";".join(filter_parts), current_label.strip("[]")
    
    def build_audio_filter(self):
        """Построение аудио фильтра с правильной синхронизацией"""
        filters = []
        
        pitch = 1.0
        speed = self.params["speed"].get()
        
        # Pitch изменение через asetrate
        # ВАЖНО: asetrate+aresample изменяет длительность!
        # Нужно компенсировать через atempo
        if self.params["audio_pitch_enabled"].get():
            pitch = self.params["audio_pitch"].get()
            if pitch != 1.0:
                sr = self.video_sample_rate
                new_sr = int(sr * pitch)
                # asetrate меняет pitch, но укорачивает/удлиняет аудио
                filters.append(f"asetrate={new_sr},aresample={sr}")
        
        # Рассчитываем итоговый atempo с компенсацией pitch
        # Формула: итоговый_tempo = speed / pitch (или speed * (1/pitch))
        # - 1/pitch компенсирует изменение длительности от asetrate
        # - speed применяет желаемую скорость
        
        if pitch != 1.0 or speed != 1.0:
            # Итоговый коэффициент tempo
            final_tempo = speed / pitch if pitch != 1.0 else speed
            
            # atempo работает в диапазоне 0.5-2.0
            # Для значений вне диапазона нужна цепочка
            self._add_atempo_chain(filters, final_tempo)
                
        return ",".join(filters) if filters else None
    
    def _add_atempo_chain(self, filters, tempo):
        """Добавление цепочки atempo для любого значения tempo"""
        if tempo == 1.0:
            return
            
        # atempo работает только в диапазоне [0.5, 2.0]
        # Для других значений нужна цепочка
        remaining = tempo
        
        while remaining < 0.5 or remaining > 2.0:
            if remaining < 0.5:
                filters.append("atempo=0.5")
                remaining /= 0.5
            elif remaining > 2.0:
                filters.append("atempo=2.0")
                remaining /= 2.0
        
        # Добавляем оставшееся значение
        if remaining != 1.0:
            filters.append(f"atempo={remaining:.6f}")
        
    def build_ffmpeg_command(self, input_path, output_path, preview_mode=False, preview_video=False):
        """Построение полной команды FFmpeg"""
        cmd = [self.ffmpeg_path, "-y"]
        
        if preview_mode:
            # Для превью берём только 1 кадр
            cmd.extend(["-ss", str(self.preview_time)])
        elif preview_video:
            # Для видео-превью берём 2 секунды
            cmd.extend(["-ss", str(self.preview_time)])
            
        cmd.extend(["-i", input_path])
        
        # Проверяем, используется ли Canvas Effect и есть ли корректные размеры видео
        canvas_enabled = self.params["canvas_enabled"].get()
        canvas_can_be_used = canvas_enabled and self.video_width > 0 and self.video_height > 0
        
        if canvas_can_be_used:
            # Complex filter для Canvas
            canvas_result = self.build_canvas_filter()
            if canvas_result:
                canvas_filter, output_label = canvas_result
                cmd.extend(["-filter_complex", canvas_filter])
                cmd.extend(["-map", f"[{output_label}]"])
                # Аудио только для видео, не для изображений (preview_mode)
                if not preview_mode:
                    cmd.extend(["-map", "0:a?"])
        else:
            # Обычные фильтры (force_build=True если canvas включен, но не может быть использован)
            filter_chain = self.build_filter_chain(force_build=canvas_enabled)
            if filter_chain:
                cmd.extend(["-vf", filter_chain])
            
        if preview_mode:
            # Только 1 кадр для превью
            cmd.extend(["-frames:v", "1"])
        elif preview_video:
            # 2 секунды для видео-превью
            cmd.extend(["-t", "2"])
            cmd.extend(["-preset", "ultrafast"])
            # Аудио фильтр
            audio_filter = self.build_audio_filter()
            if audio_filter:
                cmd.extend(["-af", audio_filter])
        else:
            # Настройки качества видео
            cmd.extend(["-b:v", "8M"])           # Видео битрейт 8 Мбит/с
            cmd.extend(["-preset", "faster"])    # Баланс скорости и качества
            
            # Настройки качества аудио
            cmd.extend(["-b:a", "192k"])         # Аудио битрейт 192 кбит/с
            
            # Аудио фильтр
            audio_filter = self.build_audio_filter()
            if audio_filter:
                cmd.extend(["-af", audio_filter])
                
            # Метаданные
            if self.params["clear_metadata"].get():
                cmd.extend(["-map_metadata", "-1"])
                
            if self.params["random_metadata"].get():
                # Список популярных программ для монтажа (реалистичные encoder)
                software_list = [
                    "Adobe Premiere Pro 2024 (Windows)",
                    "DaVinci Resolve 18.6",
                    "Vegas Pro 21.0",
                    "CapCut v11.5.0"
                ]
                
                # Выбираем случайную программу
                chosen_soft = random.choice(software_list)
                
                # Генерируем дату в пределах последних 0-7 дней (ISO 8601)
                creation_date = self._random_date()
                
                cmd.extend([
                    # Полная очистка старых метаданных
                    "-map_metadata", "-1",
                    
                    # Основные метаданные (имитация реальной программы)
                    "-metadata", f"encoder={chosen_soft}",
                    "-metadata", f"software={chosen_soft}",
                    
                    # Дата создания в формате ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
                    "-metadata", f"creation_time={creation_date}",
                ])
                
        cmd.append(output_path)
        
        return cmd
    
    def _random_date(self):
        """Генерация случайной даты в пределах последних 0-7 дней с полностью случайным временем"""
        import datetime
        now = datetime.datetime.now()
        
        # Случайное количество дней назад (0-7)
        random_days = random.randint(0, 7)
        
        # Полностью случайное время
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        random_seconds = random.randint(0, 59)
        
        # Формируем дату
        random_date = now - datetime.timedelta(days=random_days)
        random_date = random_date.replace(
            hour=random_hours,
            minute=random_minutes,
            second=random_seconds,
            microsecond=0
        )
        
        # Возвращаем в формате ISO 8601 с Z (UTC)
        return random_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
    def get_display_command(self):
        """Получение команды для отображения"""
        if not self.video_path:
            return "ffmpeg -i input.mp4 output.mp4"
            
        parts = ["ffmpeg", "-i", '"input.mp4"']
        
        canvas_enabled = self.params["canvas_enabled"].get()
        
        if canvas_enabled:
            # Упрощённое отображение для Canvas
            scale = self.params["canvas_scale"].get()
            blur = int(self.params["canvas_blur"].get())
            radius = int(self.params["canvas_corner_radius"].get())
            parts.append(f'-filter_complex "Canvas: scale={scale:.2f}, blur={blur}, radius={radius}"')
        else:
            filter_chain = self.build_filter_chain()
            if filter_chain:
                parts.extend(["-vf", f'"{filter_chain}"'])
        
        # Audio filter
        audio_filter = self.build_audio_filter()
        if audio_filter:
            parts.extend(["-af", f'"{audio_filter}"'])
            
        # Metadata
        if self.params["clear_metadata"].get():
            parts.append("-map_metadata -1")
        if self.params["random_metadata"].get():
            parts.append("-metadata title=RANDOM")
            
        parts.append('"output.mp4"')
        
        return " ".join(parts)
        
    def refresh_preview(self):
        """Обновление превью"""
        if not self.video_path:
            return
            
        # Обновить команду
        self.cmd_label.configure(text=self.get_display_command())
        
        # Генерация превью в отдельном потоке
        threading.Thread(target=self._generate_preview, daemon=True).start()
        
    def _generate_preview(self):
        """Генерация кадра превью"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
                
            cmd = self.build_ffmpeg_command(self.video_path, tmp_path, preview_mode=True)
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                self._display_preview(tmp_path)
            else:
                print(f"FFmpeg error: {result.stderr}")
                
            # Удалить временный файл
            try:
                os.unlink(tmp_path)
            except:
                pass
                
        except Exception as e:
            print(f"Ошибка генерации превью: {e}")
            
    def _display_preview(self, image_path):
        """Отображение превью в интерфейсе"""
        try:
            img = Image.open(image_path)
            
            # Масштабирование под размер контейнера
            container_width = self.preview_container.winfo_width() - 20
            container_height = self.preview_container.winfo_height() - 20
            
            if container_width < 100:
                container_width = 750
            if container_height < 100:
                container_height = 450
                
            # Сохраняем пропорции
            img_ratio = img.width / img.height
            container_ratio = container_width / container_height
            
            if img_ratio > container_ratio:
                new_width = container_width
                new_height = int(container_width / img_ratio)
            else:
                new_height = container_height
                new_width = int(container_height * img_ratio)
                
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Конвертация для Tkinter
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(new_width, new_height))
            
            # Обновление в главном потоке
            self.after(0, lambda: self._update_preview_label(photo))
            
        except Exception as e:
            print(f"Ошибка отображения: {e}")
            
    def _update_preview_label(self, photo):
        """Обновление лейбла превью"""
        self.preview_label.configure(image=photo, text="")
        self.preview_label.image = photo  # Сохраняем ссылку
        
        # Обновить время
        current = self.format_time(self.preview_time)
        total = self.format_time(self.video_duration)
        self.time_label.configure(text=f"{current} / {total}")
        
    def format_time(self, seconds):
        """Форматирование времени"""
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:05.2f}"
        
    def _on_timeline_change(self, value):
        """Обработка изменения таймлайна"""
        if self.video_duration > 0:
            self.preview_time = (float(value) / 100) * self.video_duration
            self.refresh_preview()
            
    def toggle_play(self):
        """Включение/выключение воспроизведения превью"""
        if not self.video_path:
            return
            
        if self.is_playing:
            self.is_playing = False
            self.play_btn.configure(text="▶")
        else:
            self.is_playing = True
            self.play_btn.configure(text="⏸")
            self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
            self.play_thread.start()
            
    def _play_loop(self):
        """Цикл воспроизведения"""
        import time
        
        while self.is_playing and self.preview_time < self.video_duration:
            self.preview_time += 0.5  # Шаг 0.5 секунды
            
            # Обновить слайдер
            progress = (self.preview_time / self.video_duration) * 100
            self.after(0, lambda p=progress: self.timeline_slider.set(p))
            
            # Обновить превью
            self.refresh_preview()
            
            time.sleep(0.5)
            
        self.after(0, lambda: self.play_btn.configure(text="▶"))
        self.is_playing = False
        
    def preview_video_clip(self):
        """Создание и воспроизведение 2-секундного превью видео"""
        if not self.video_path:
            messagebox.showwarning("Предупреждение", "Сначала загрузите видео!")
            return
            
        def do_preview():
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                    tmp_path = tmp.name
                    
                cmd = self.build_ffmpeg_command(self.video_path, tmp_path, preview_video=True)
                
                self.after(0, lambda: self.refresh_btn.configure(text="⏳"))
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0 and os.path.exists(tmp_path):
                    # Открыть видео в плеере по умолчанию
                    os.startfile(tmp_path)
                else:
                    self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка рендеринга:\n{result.stderr[:500]}"))
                    
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.after(0, lambda: self.refresh_btn.configure(text="🔄"))
                
        threading.Thread(target=do_preview, daemon=True).start()
        
    def reset_params(self):
        """Сброс всех параметров"""
        defaults = {
            "brightness": 0,
            "contrast": 1,
            "saturation": 1,
            "gamma": 1,
            "gamma_r": 1,
            "gamma_g": 1,
            "gamma_b": 1,
            "sharpen": 0,
            "blur": 0,
            "denoise_strength": 0,
            "vignette": 0,
            "rotation": 0,
            "hflip": False,
            "vflip": False,
            "speed": 1.0,
            "hue": 0,
            "colorize": False,
            "negate": False,
            "eq_preset": "none",
            # Canvas
            "canvas_enabled": False,
            "canvas_scale": 0.85,
            "canvas_blur": 25,
            "canvas_corner_radius": 20,
            "canvas_corner_smooth": 1.0,
            "canvas_bg_zoom": 1.15,
            "canvas_noise": 0,
            "canvas_vignette": 0.3,
            # Audio
            "audio_pitch": 1.0,
            "audio_pitch_enabled": False,
            # Metadata
            "clear_metadata": True,
            "random_metadata": True,
        }
        
        for name, value in defaults.items():
            if name in self.params:
                self.params[name].set(value)
                
        self.params["scale_width"].set("")
        self.params["scale_height"].set("")
        self.params["custom_filter"].set("")
        self.custom_entry.delete("1.0", "end")
        
        if self.video_path:
            self.params["crop_x"].set(0)
            self.params["crop_y"].set(0)
            self.params["crop_w"].set(self.video_width)
            self.params["crop_h"].set(self.video_height)
            
        self.refresh_preview()
        
    def copy_command(self):
        """Копирование команды в буфер обмена"""
        cmd = self.get_display_command()
        self.clipboard_clear()
        self.clipboard_append(cmd)
        
        # Временное сообщение
        original_text = self.cmd_label.cget("text")
        self.cmd_label.configure(text="✅ Команда скопирована!")
        self.after(1500, lambda: self.cmd_label.configure(text=original_text))
    
    def get_uniquify_params(self):
        """Получение параметров уникализации как словарь"""
        return {
            # Canvas Effect
            "canvas_enabled": self.params["canvas_enabled"].get(),
            "canvas_scale": round(self.params["canvas_scale"].get(), 3),
            "canvas_blur": int(self.params["canvas_blur"].get()),
            "canvas_corner_radius": int(self.params["canvas_corner_radius"].get()),
            "canvas_corner_smooth": round(self.params["canvas_corner_smooth"].get(), 2),
            "canvas_bg_zoom": round(self.params["canvas_bg_zoom"].get(), 3),
            "canvas_noise": int(self.params["canvas_noise"].get()),
            "canvas_vignette": round(self.params["canvas_vignette"].get(), 2),
            
            # Audio
            "audio_pitch_enabled": self.params["audio_pitch_enabled"].get(),
            "audio_pitch": round(self.params["audio_pitch"].get(), 4),
            
            # Metadata
            "clear_metadata": self.params["clear_metadata"].get(),
            "random_metadata": self.params["random_metadata"].get(),
            
            # Color correction (if changed from defaults)
            "brightness": round(self.params["brightness"].get(), 3),
            "contrast": round(self.params["contrast"].get(), 3),
            "saturation": round(self.params["saturation"].get(), 3),
            "gamma": round(self.params["gamma"].get(), 3),
            "hue": round(self.params["hue"].get(), 1),
        }
    
    def copy_params_json(self):
        """Копирование параметров как JSON"""
        params = self.get_uniquify_params()
        json_str = json.dumps(params, indent=2, ensure_ascii=False)
        
        self.clipboard_clear()
        self.clipboard_append(json_str)
        messagebox.showinfo("Скопировано", "Параметры скопированы как JSON!\n\nВставьте в другую программу.")
    
    def copy_params_python(self):
        """Копирование параметров как Python код"""
        params = self.get_uniquify_params()
        
        lines = ["# Параметры уникализации FFmpeg", "uniquify_params = {"]
        for key, value in params.items():
            if isinstance(value, bool):
                lines.append(f'    "{key}": {value},')
            elif isinstance(value, str):
                lines.append(f'    "{key}": "{value}",')
            else:
                lines.append(f'    "{key}": {value},')
        lines.append("}")
        
        # Добавляем код применения
        lines.extend([
            "",
            "# Пример применения параметров:",
            "def apply_params(editor, params):",
            "    for key, value in params.items():",
            "        if key in editor.params:",
            "            editor.params[key].set(value)",
        ])
        
        python_str = "\n".join(lines)
        
        self.clipboard_clear()
        self.clipboard_append(python_str)
        messagebox.showinfo("Скопировано", "Параметры скопированы как Python код!\n\nВставьте в ваш скрипт.")
    
    def apply_params_from_dict(self, params_dict):
        """Применение параметров из словаря (для импорта)"""
        for key, value in params_dict.items():
            if key in self.params:
                self.params[key].set(value)
        self.refresh_preview()
        
    def export_video(self):
        """Экспорт обработанного видео"""
        if not self.video_path:
            messagebox.showwarning("Предупреждение", "Сначала загрузите видео!")
            return
            
        # Выбор файла для сохранения
        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[
                ("MP4", "*.mp4"),
                ("AVI", "*.avi"),
                ("MKV", "*.mkv"),
                ("WebM", "*.webm"),
            ]
        )
        
        if not output_path:
            return
            
        # Запуск экспорта в отдельном потоке
        self.export_btn.configure(text="⏳ Экспорт...", state="disabled")
        
        def do_export():
            try:
                cmd = self.build_ffmpeg_command(self.video_path, output_path, preview_mode=False)
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    self.after(0, lambda: messagebox.showinfo("Готово", f"Видео сохранено:\n{output_path}"))
                else:
                    self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка FFmpeg:\n{result.stderr[:500]}"))
                    
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.after(0, lambda: self.export_btn.configure(text="💾 Экспорт видео", state="normal"))
                
        threading.Thread(target=do_export, daemon=True).start()


if __name__ == "__main__":
    app = FFmpegPreviewEditor()
    app.mainloop()
