import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io
import re

# Настройка страницы
st.set_page_config(page_title="Анализ пожаров", page_icon="🔥", layout="wide")

# Пробуем импортировать все необходимые библиотеки
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("Plotly не установлен. Установите: pip install plotly")

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    st.warning("Openpyxl не установлен. Установите: pip install openpyxl")

# Функции для создания графиков
def create_chart(data, chart_type='line', **kwargs):
    """Умный создатель графиков с fallback"""
    if PLOTLY_AVAILABLE and not data.empty:
        return create_plotly_chart(data, chart_type, **kwargs)
    else:
        return create_simple_chart(data, chart_type, **kwargs)

def create_plotly_chart(data, chart_type, **kwargs):
    """Создание Plotly графиков"""
    try:
        if chart_type == 'line' and not data.empty:
            fig = px.line(data, x=kwargs.get('x'), y=kwargs.get('y'), 
                         title=kwargs.get('title'), template='plotly_white')
            fig.update_layout(xaxis_title=kwargs.get('x'), yaxis_title=kwargs.get('y'))
            return st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == 'bar' and not data.empty:
            fig = px.bar(data, x=kwargs.get('x'), y=kwargs.get('y'),
                        title=kwargs.get('title'), orientation=kwargs.get('orientation'),
                        template='plotly_white')
            return st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == 'pie' and not data.empty:
            fig = px.pie(data, names=kwargs.get('names'), values=kwargs.get('values'),
                        title=kwargs.get('title'))
            return st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(f"Ошибка создания графика: {e}")
        return create_simple_chart(data, chart_type, **kwargs)

def create_simple_chart(data, chart_type, **kwargs):
    """Создание простых графиков или таблиц"""
    try:
        if chart_type == 'line' and not data.empty and kwargs.get('y') in data.columns:
            st.line_chart(data[kwargs.get('y')])
        elif chart_type == 'bar' and not data.empty and kwargs.get('y') in data.columns:
            st.bar_chart(data[kwargs.get('y')])
        else:
            st.dataframe(data)
    except Exception as e:
        st.error(f"Ошибка простого графика: {e}")
        st.dataframe(data)

# Функция для загрузки и обработки данных
def load_data(uploaded_file):
    """Загрузка данных из Excel файла"""
    try:
        if OPENPYXL_AVAILABLE:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            df = pd.read_excel(uploaded_file)
        
        # Предобработка данных
        df = preprocess_data(df)
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return None

def preprocess_data(df):
    """Предобработка данных с вашей структурой"""
    # Приводим названия колонок к нижнему регистру для удобства
    df.columns = df.columns.str.lower().str.strip()
    
    # Создаем копию для безопасной работы
    df_processed = df.copy()
    
    # Создаем колонку с количеством пожаров (каждая строка = 1 пожар)
    df_processed['количество_пожаров'] = 1
    
    # Обработка даты
    date_columns = ['дата возникновения', 'дата']
    date_column = None
    for col in date_columns:
        if col in df_processed.columns:
            date_column = col
            break
    
    if date_column:
        df_processed['дата'] = pd.to_datetime(df_processed[date_column], errors='coerce')
        df_processed['год'] = df_processed['дата'].dt.year
        df_processed['месяц'] = df_processed['дата'].dt.month
        df_processed['месяц_название'] = df_processed['дата'].dt.month_name()
    else:
        # Если даты нет, создаем фиктивные год и месяц
        df_processed['год'] = 2023
        df_processed['месяц'] = 1
        df_processed['месяц_название'] = 'Январь'
    
    # Переименовываем основные колонки если они есть
    column_mapping = {
        'муниципальный район': 'район',
        'населенный пункт': 'населенный_пункт', 
        'улица': 'улица',
        'дом': 'дом',
        'геоточка': 'геоточка',
        'объединенный адрес': 'адрес',
        'объект пожара (загорания)': 'объект',
        'объект пожара': 'объект',
        'причина пожара': 'причина',
        'погибло людей: всего': 'погибло',
        'в  т.ч. погибло детей': 'погибло_детей', 
        'получили травмы: всего': 'травмы',
        'в  т.ч. получили травмы: детей': 'травмы_детей',
        'спасено на пожаре людей': 'спасено',
        'эвакуировано на пожаре людей': 'эвакуировано'
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in df_processed.columns and new_col not in df_processed.columns:
            df_processed[new_col] = df_processed[old_col]
    
    # УЛУЧШЕННАЯ ОБРАБОТКА ЧИСЛОВЫХ ДАННЫХ
    df_processed = process_numeric_data(df_processed)
    
    # ОБРАБОТКА ГЕОДАННЫХ
    df_processed = process_geodata(df_processed)
    
    # УЛУЧШЕННАЯ ОБРАБОТКА ПРИЧИН
    df_processed = improve_cause_analysis(df_processed)
    
    # Заполняем пропуски в текстовых колонках
    text_columns = ['район', 'объект', 'причина', 'населенный_пункт']
    for col in text_columns:
        if col in df_processed.columns:
            df_processed[col] = df_processed[col].fillna('Не указано')
        else:
            df_processed[col] = 'Не указано'
    
    return df_processed

def process_numeric_data(df):
    """Улучшенная обработка числовых данных с объединением взрослых и детей"""
    # Список числовых колонок для обработки
    numeric_columns = [
        'погибло', 'травмы', 'погибло_детей', 'травмы_детей', 
        'спасено', 'эвакуировано'
    ]
    
    st.sidebar.write("**Обработка числовых данных:**")
    
    for col in numeric_columns:
        if col in df.columns:
            # Обрабатываем данные
            df[col] = df[col].replace(['', ' ', '  ', None, 'None', 'NaN', 'nan'], 0)
            df[col] = df[col].astype(str).str.replace(',', '.')
            df[col] = df[col].astype(str).str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(0)
            df[col] = df[col].astype(int)
            
            non_zero = (df[col] > 0).sum()
            st.sidebar.write(f"{col} > 0: {non_zero} записей")
        else:
            df[col] = 0
            st.sidebar.write(f"{col}: колонка не найдена")
    
    # ОБЪЕДИНЯЕМ ДАННЫЕ О ВЗРОСЛЫХ И ДЕТЯХ
    df['всего_погибло'] = df['погибло'] + df['погибло_детей']
    df['всего_травмы'] = df['травмы'] + df['травмы_детей']
    
    # Показываем итоговую статистику
    total_deaths = df['всего_погибло'].sum()
    total_injuries = df['всего_травмы'].sum()
    child_deaths = df['погибло_детей'].sum()
    child_injuries = df['травмы_детей'].sum()
    
    st.sidebar.success(f"Итого - Погибших: {total_deaths} (детей: {child_deaths})")
    st.sidebar.success(f"Итого - Пострадавших: {total_injuries} (детей: {child_injuries})")
    
    return df

def process_geodata(df):
    """Обработка геоданных с правильной проверкой координат"""
    # Проверяем наличие геоточек
    if 'геоточка' in df.columns:
        try:
            # Разделяем геоточку на два числа
            coords = df['геоточка'].astype(str).str.split(' ', expand=True)
            
            if len(coords.columns) >= 2:
                # Получаем оба числа
                num1 = pd.to_numeric(coords[0], errors='coerce')
                num2 = pd.to_numeric(coords[1], errors='coerce')
                
                # Создаем колонки для координат
                df['lat'] = None
                df['lon'] = None
                
                valid_count = 0
                invalid_count = 0
                
                # Проверяем каждую строку отдельно
                for idx in df.index:
                    if pd.isna(num1[idx]) or pd.isna(num2[idx]):
                        invalid_count += 1
                        continue
                    
                    # Пробуем вариант 1: num1 = широта, num2 = долгота
                    if (-90 <= num1[idx] <= 90) and (-180 <= num2[idx] <= 180):
                        df.at[idx, 'lat'] = num1[idx]  # широта
                        df.at[idx, 'lon'] = num2[idx]  # долгота
                        valid_count += 1
                    
                    # Пробуем вариант 2: num1 = долгота, num2 = широта  
                    elif (-90 <= num2[idx] <= 90) and (-180 <= num1[idx] <= 180):
                        df.at[idx, 'lat'] = num2[idx]  # широта
                        df.at[idx, 'lon'] = num1[idx]  # долгота
                        valid_count += 1
                    
                    else:
                        invalid_count += 1
                
                # Преобразуем в числовой формат
                df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
                df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
                
                # Убираем строки с некорректными координатами
                valid_coords = df.dropna(subset=['lat', 'lon'])
                
                st.sidebar.success(f"Обработано геоточек: {valid_count}/{len(df)}")
                
                if invalid_count > 0:
                    st.sidebar.warning(f"Некорректные координаты: {invalid_count} записей")
                
                # Показываем примеры обработанных координат
                if not valid_coords.empty:
                    with st.sidebar.expander("📍 Примеры координат"):
                        sample = valid_coords[['геоточка', 'lat', 'lon']].head(3)
                        for _, row in sample.iterrows():
                            st.write(f"{row['геоточка']} → lat:{row['lat']:.6f}, lon:{row['lon']:.6f}")
                
        except Exception as e:
            st.sidebar.error(f"Ошибка обработки геоданных: {e}")
    
    return df

def improve_cause_analysis(df):
    """Улучшенный анализ причин пожаров"""
    # Ищем колонки, которые могут содержать информацию о причинах
    cause_columns = []
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ['причина', 'cause', 'reason']):
            cause_columns.append(col)
    
    # Если нашли колонки с причинами, объединяем их
    if cause_columns:
        st.sidebar.info(f"Найдены колонки с причинами: {cause_columns}")
        
        # Создаем объединенную колонку причин
        causes_combined = []
        for idx, row in df.iterrows():
            causes = []
            for col in cause_columns:
                if pd.notna(row[col]) and str(row[col]).strip() not in ['', 'nan', 'None']:
                    causes.append(str(row[col]).strip())
            
            if causes:
                causes_combined.append('; '.join(causes))
            else:
                causes_combined.append('Не указана')
        
        df['причина_объединенная'] = causes_combined
    else:
        # Если нет специальных колонок, ищем в других текстовых колонках
        df['причина_объединенная'] = 'Не указана'
    
    # Очистка и категоризация причин
    df['причина_очищенная'] = df['причина_объединенная'].apply(clean_and_categorize_cause)
    
    return df

def clean_and_categorize_cause(cause_text):
    """Очистка и категоризация причин пожаров"""
    if pd.isna(cause_text) or cause_text in ['', 'nan', 'None', 'Не указана']:
        return 'Причина не указана'
    
    text = str(cause_text).lower().strip()
    
    # Категоризация причин
    cause_patterns = {
        'Электрооборудование': [
            'электр', 'проводка', 'короткое замыкание', 'электрич', 'розетка', 
            'выключатель', 'сеть', 'напряжение', 'эл.', 'эл.оборудование'
        ],
        'Неосторожное обращение с огнем': [
            'неосторож', 'курение', 'спички', 'зажигалка', 'огонь', 'костер',
            'поджог', 'умышлен', 'детская шалость'
        ],
        'Бытовая техника': [
            'телевизор', 'холодильник', 'чайник', 'утюг', 'микроволновка',
            'обогреватель', 'отопление', 'печь', 'камин'
        ],
        'Природные причины': [
            'молния', 'гроза', 'солнце', 'засуха', 'природн', 'самовозгорание'
        ],
        'Техногенные причины': [
            'производств', 'техник', 'оборудование', 'автомобиль', 'транспорт',
            'газ', 'топливо', 'химич', 'горюч'
        ],
        'Строительные причины': [
            'ремонт', 'строительств', 'сварка', 'отделк', 'покраска'
        ],
        'Нарушение правил пожарной безопасности': [
            'нарушение', 'правила', 'пожарная безопасность', 'ппб', 'нормы'
        ]
    }
    
    # Проверяем категории
    for category, patterns in cause_patterns.items():
        for pattern in patterns:
            if pattern in text:
                return category
    
    # Если не нашли категорию, но текст не пустой
    if len(text) > 10 and text not in ['не указана', 'нет', 'не установлена']:
        return 'Другие причины'
    
    return 'Причина не указана'

# ФУНКЦИИ АНАЛИЗА - ОПРЕДЕЛЕНЫ ПЕРЕД ИСПОЛЬЗОВАНИЕМ
def analyze_fire_trends(df):
    """Анализ динамики пожаров по годам"""
    st.subheader("1. Динамика количества пожаров по годам")
    
    if 'год' in df.columns:
        # Собираем все показатели
        yearly_data = df.groupby('год').agg({
            'количество_пожаров': 'count',
            'всего_погибло': 'sum',
            'всего_травмы': 'sum',
            'погибло_детей': 'sum',
            'травмы_детей': 'sum'
        }).reset_index()
        
        if not yearly_data.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                create_chart(yearly_data, 'line', x='год', y='количество_пожаров', 
                            title='Динамика количества пожаров по годам')
            
            with col2:
                # Показываем метрики
                if len(yearly_data) > 1:
                    last_year = yearly_data.iloc[-1]
                    prev_year = yearly_data.iloc[-2]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        delta_fires = last_year['количество_пожаров'] - prev_year['количество_пожаров']
                        st.metric("Пожары", f"{last_year['количество_пожаров']:.0f}", 
                                 f"{delta_fires:+.0f}")
                    
                    with col2:
                        delta_deaths = last_year['всего_погибло'] - prev_year['всего_погибло']
                        st.metric("Всего погибших", f"{last_year['всего_погибло']:.0f}", 
                                 f"{delta_deaths:+.0f}")
                    
                    with col3:
                        delta_injuries = last_year['всего_травмы'] - prev_year['всего_травмы']
                        st.metric("Всего пострадавших", f"{last_year['всего_травмы']:.0f}", 
                                 f"{delta_injuries:+.0f}")
                    
                    with col4:
                        delta_children = (last_year['погибло_детей'] + last_year['травмы_детей']) - \
                                       (prev_year['погибло_детей'] + prev_year['травмы_детей'])
                        st.metric("Пострадало детей", 
                                 f"{(last_year['погибло_детей'] + last_year['травмы_детей']):.0f}", 
                                 f"{delta_children:+.0f}")
                
                # Детальная статистика по жертвам
                with st.expander("📊 Детальная статистика по погибшим и пострадавшим"):
                    if len(yearly_data) > 0:
                        current_year = yearly_data.iloc[-1]
                        st.write(f"**За {current_year['год']} год:**")
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Всего погибших", f"{current_year['всего_погибло']:.0f}")
                        col2.metric("в т.ч. детей", f"{current_year['погибло_детей']:.0f}")
                        col3.metric("Всего пострадавших", f"{current_year['всего_травмы']:.0f}")
                        col4.metric("в т.ч. детей", f"{current_year['травмы_детей']:.0f}")
            
            # График погибших и пострадавших
            if yearly_data['всего_погибло'].sum() > 0 or yearly_data['всего_травмы'].sum() > 0:
                fig = px.line(yearly_data, x='год', y=['всего_погибло', 'всего_травмы'],
                            title='Динамика погибших и пострадавших',
                            labels={'value': 'Количество людей', 'variable': 'Показатель'})
                fig.update_traces(line=dict(width=3))
                st.plotly_chart(fig, use_container_width=True)
                
        else:
            st.info("Нет данных для анализа динамики")
    else:
        st.info("Отсутствует колонка с годом для анализа динамики")

def analyze_district_map(df):
    """Отображение пожаров на карте с использованием реальных геоточек"""
    st.subheader("2.2 Распределение пожаров по районам на карте")
    
    # Проверяем наличие координат
    if 'lat' in df.columns and 'lon' in df.columns:
        # Фильтруем только корректные координаты
        map_data = df.dropna(subset=['lat', 'lon']).copy()
        
        # Дополнительная проверка на валидность координат
        map_data = map_data[
            (map_data['lat'] >= -90) & (map_data['lat'] <= 90) &
            (map_data['lon'] >= -180) & (map_data['lon'] <= 180)
        ]
        
        if map_data.empty:
            st.warning("Нет данных с корректными координатами для построения карты")
            return
        
        st.info(f"Отображается {len(map_data)} точек из {len(df)} записей")
        
        # Агрегируем данные для карты (группируем по координатам)
        if 'район' in df.columns:
            aggregated_data = map_data.groupby(['район', 'lat', 'lon']).agg({
                'количество_пожаров': 'count',
                'погибло': 'sum',
                'травмы': 'sum',
                'погибло_детей': 'sum',
                'травмы_детей': 'sum'
            }).reset_index()
        else:
            aggregated_data = map_data.groupby(['lat', 'lon']).agg({
                'количество_пожаров': 'count',
                'погибло': 'sum',
                'травмы': 'sum',
                'погибло_детей': 'sum',
                'травмы_детей': 'sum'
            }).reset_index()
            aggregated_data['район'] = 'Не указан'
        
        if PLOTLY_AVAILABLE:
            try:
                # Создаем карту
                fig = px.scatter_mapbox(
                    aggregated_data,
                    lat="lat",
                    lon="lon", 
                    size="количество_пожаров",
                    color="количество_пожаров",
                    hover_name="район",
                    hover_data={
                        'количество_пожаров': True,
                        'погибло': True,
                        'травмы': True,
                        'погибло_детей': True,
                        'травмы_детей': True,
                        'lat': False,
                        'lon': False
                    },
                    color_continuous_scale=px.colors.sequential.Reds,
                    size_max=20,
                    zoom=4,
                    title="Карта пожаров по геоточкам"
                )
                fig.update_layout(mapbox_style="open-street-map")
                fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # Статистика по карте
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Точек на карте", len(aggregated_data))
                with col2:
                    st.metric("Всего пожаров", aggregated_data['количество_пожаров'].sum())
                with col3:
                    st.metric("Погибло на карте", aggregated_data['погибло'].sum())
                with col4:
                    st.metric("Пострадало на карте", aggregated_data['травмы'].sum())
                
            except Exception as e:
                st.error(f"Не удалось создать карту: {e}")
        else:
            st.info("Для отображения карты установите plotly: pip install plotly")
        
        # Детальная информация о геоданных
        with st.expander("📋 Детальная информация о геоданных"):
            st.write("**Статистика координат:**")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"Широта: {map_data['lat'].min():.4f} - {map_data['lat'].max():.4f}")
                st.write(f"Средняя широта: {map_data['lat'].mean():.4f}")
            with col2:
                st.write(f"Долгота: {map_data['lon'].min():.4f} - {map_data['lon'].max():.4f}")
                st.write(f"Средняя долгота: {map_data['lon'].mean():.4f}")
            
            st.write("**Пример геоданных:**")
            display_cols = ['район', 'населенный_пункт', 'lat', 'lon', 'количество_пожаров', 'погибло', 'травмы']
            display_cols = [col for col in display_cols if col in map_data.columns]
            st.dataframe(map_data[display_cols].head(10), use_container_width=True)
            
    else:
        st.warning("""
        **Координаты не найдены!**
        
        Для построения карты нужна колонка 'геоточка' с данными в формате "долгота широта"
        Пример: 131.090314 60.465566
        """)


def analyze_district_distribution(df):
    """Распределение пожаров по районам"""
    st.subheader("2.1 Рейтинг районов по количеству пожаров")
    
    if 'район' in df.columns:
        district_data = df.groupby('район').agg({
            'количество_пожаров': 'count',
            'всего_погибло': 'sum',
            'всего_травмы': 'sum',
            'погибло_детей': 'sum',
            'травмы_детей': 'sum'
        }).reset_index()
        
        district_data = district_data.sort_values('количество_пожаров', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if not district_data.empty:
                create_chart(district_data.head(10), 'bar', x='район', y='количество_пожаров',
                            title='Топ-10 районов по количеству пожаров')
            else:
                st.info("Нет данных для построения графика")
        
        with col2:
            if not district_data.empty:
                st.write("**Рейтинг районов (первые 10):**")
                display_data = district_data.head(10).copy()
                
                # Переименовываем колонки для красивого отображения
                display_data = display_data.rename(columns={
                    'район': 'Район',
                    'количество_пожаров': 'Пожары',
                    'всего_погибло': 'Погибло',
                    'всего_травмы': 'Пострадало'
                })
                
                # Добавляем долю от общего количества
                total_fires = display_data['Пожары'].sum()
                display_data['Доля %'] = (display_data['Пожары'] / total_fires * 100).round(1)
                
                st.dataframe(display_data[['Район', 'Пожары', 'Погибло', 'Пострадало', 'Доля %']], 
                           use_container_width=True)
                
                # Общая статистика
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Всего районов", df['район'].nunique())
                with col2:
                    st.metric("Среднее пожаров на район", 
                             f"{district_data['количество_пожаров'].mean():.1f}")
                with col3:
                    st.metric("Всего погибших", f"{district_data['всего_погибло'].sum():.0f}")
                
                # Детальная статистика по детям
                if (district_data['погибло_детей'].sum() > 0 or 
                    district_data['травмы_детей'].sum() > 0):
                    with st.expander("📊 Статистика по детям"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Погибло детей", f"{district_data['погибло_детей'].sum():.0f}")
                        with col2:
                            st.metric("Пострадало детей", f"{district_data['травмы_детей'].sum():.0f}")
    else:
        st.info("Отсутствует колонка с районами")


def analyze_causes(df):
    """Анализ причин пожаров"""
    st.subheader("3. Основные причины возникновения пожаров")
    
    if 'причина_очищенная' in df.columns:
        # Анализ очищенных причин
        causes_data = df.groupby('причина_очищенная').agg({
            'количество_пожаров': 'count',
            'всего_погибло': 'sum',
            'всего_травмы': 'sum',
            'погибло_детей': 'sum',
            'травмы_детей': 'sum'
        }).reset_index()
        
        causes_data = causes_data.sort_values('количество_пожаров', ascending=False)
        
        if not causes_data.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                plot_data = causes_data.copy()
                if len(plot_data) > 1 and plot_data.iloc[0]['причина_очищенная'] == 'Причина не указана':
                    if plot_data.iloc[0]['количество_пожаров'] / plot_data['количество_пожаров'].sum() > 0.8:
                        other_causes = plot_data[plot_data['причина_очищенная'] != 'Причина не указана']
                        if not other_causes.empty:
                            plot_data = other_causes.head(7)
                            st.info("Показаны известные причины (большинство записей без указания причины)")
                
                create_chart(plot_data.head(8), 'pie', names='причина_очищенная', 
                            values='количество_пожаров', title='Распределение по причинам')
            
            with col2:
                st.write("**Статистика по причинам:**")
                display_causes = causes_data.copy()
                display_causes['доля'] = (display_causes['количество_пожаров'] / display_causes['количество_пожаров'].sum() * 100).round(1)
                display_causes = display_causes.rename(columns={
                    'причина_очищенная': 'Причина',
                    'количество_пожаров': 'Количество',
                    'всего_погибло': 'Погибло',
                    'всего_травмы': 'Пострадало',
                    'доля': 'Доля (%)'
                })
                st.dataframe(display_causes[['Причина', 'Количество', 'Погибло', 'Пострадало', 'Доля (%)']], 
                           use_container_width=True)
        
        # Анализ самых опасных причин
        if df['всего_погибло'].sum() > 0:
            st.subheader("Причины с наибольшими последствиями")
            
            dangerous_causes = df.groupby('причина_очищенная').agg({
                'количество_пожаров': 'count',
                'всего_погибло': 'sum',
                'всего_травмы': 'sum'
            }).reset_index()
            
            dangerous_causes = dangerous_causes[dangerous_causes['всего_погибло'] > 0]
            dangerous_causes['смертность_%'] = (dangerous_causes['всего_погибло'] / dangerous_causes['количество_пожаров'] * 100).round(2)
            dangerous_causes['травматизм_%'] = (dangerous_causes['всего_травмы'] / dangerous_causes['количество_пожаров'] * 100).round(2)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**По количеству погибших:**")
                display_deaths = dangerous_causes.sort_values('всего_погибло', ascending=False).head(5)
                display_deaths = display_deaths.rename(columns={
                    'причина_очищенная': 'Причина',
                    'количество_пожаров': 'Пожары',
                    'всего_погибло': 'Погибло',
                    'смертность_%': 'Смертность %'
                })
                st.dataframe(display_deaths[['Причина', 'Пожары', 'Погибло', 'Смертность %']], 
                           use_container_width=True)
            
            with col2:
                st.write("**По уровню смертности:**")
                high_mortality = dangerous_causes.sort_values('смертность_%', ascending=False).head(5)
                display_mortality = high_mortality.rename(columns={
                    'причина_очищенная': 'Причина',
                    'количество_пожаров': 'Пожары',
                    'всего_погибло': 'Погибло',
                    'смертность_%': 'Смертность %'
                })
                st.dataframe(display_mortality[['Причина', 'Пожары', 'Погибло', 'Смертность %']], 
                           use_container_width=True)
    
    else:
        st.info("Не удалось определить причины пожаров в данных")

def analyze_locations(df):
    """Анализ мест возникновения"""
    st.subheader("4. Наиболее частые места возникновения пожаров")
    
    if 'объект' in df.columns:
        locations_data = df.groupby('объект').agg({
            'количество_пожаров': 'count'
        }).reset_index()
        
        locations_data = locations_data.sort_values('количество_пожаров', ascending=False)
        
        if not locations_data.empty:
            create_chart(locations_data.head(10), 'bar', x='объект', y='количество_пожаров',
                        title='Топ-10 объектов пожаров')
        else:
            st.info("Нет данных о местах возникновения пожаров")
    else:
        st.info("Отсутствует колонка с объектами пожаров")

def analyze_seasonality(df):
    """Анализ сезонности"""
    st.subheader("5. Сезонность пожаров (по месяцам)")
    
    if 'месяц' in df.columns:
        monthly_data = df.groupby('месяц').agg({
            'количество_пожаров': 'count'
        }).reset_index()
        
        if not monthly_data.empty:
            # Преобразуем номера месяцев в названия
            month_names = {
                1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 
                5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
                9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
            }
            monthly_data['месяц_название'] = monthly_data['месяц'].map(month_names)
            
            create_chart(monthly_data, 'line', x='месяц_название', y='количество_пожаров',
                        title='Сезонность пожаров по месяцам')
        else:
            st.info("Нет данных для анализа сезонности")
    else:
        st.info("Отсутствуют данные о месяцах для анализа сезонности")

def analyze_district_dynamics(df):
    """Динамика по районам"""
    st.subheader("6. Динамика показателей по районам")
    
    if 'район' in df.columns and 'год' in df.columns:
        available_districts = df['район'].unique()
        if len(available_districts) > 0:
            districts = st.multiselect("Выберите районы для анализа:", 
                                     available_districts, 
                                     default=available_districts[:min(3, len(available_districts))])
            
            if districts:
                filtered_data = df[df['район'].isin(districts)]
                district_yearly = filtered_data.groupby(['год', 'район']).agg({
                    'количество_пожаров': 'count'
                }).reset_index()
                
                if not district_yearly.empty:
                    if PLOTLY_AVAILABLE:
                        fig = px.line(district_yearly, x='год', y='количество_пожаров', 
                                     color='район', title='Динамика пожаров по выбранным районам')
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        pivot_data = district_yearly.pivot(index='год', columns='район', values='количество_пожаров')
                        st.line_chart(pivot_data)
                else:
                    st.info("Нет данных для выбранных районов")
        else:
            st.info("Нет данных о районах")
    else:
        st.info("Отсутствуют данные о районах или годах для анализа динамики")

def analyze_comparison(df):
    """Сравнение с аналогичным периодом прошлого года"""
    st.subheader("7. Сравнение с аналогичным периодом прошлого года (АППГ)")
    
    if 'год' in df.columns and 'район' in df.columns:
        current_year = df['год'].max()
        previous_year = current_year - 1
        
        current_data = df[df['год'] == current_year].groupby('район').agg({
            'количество_пожаров': 'count',
            'погибло': 'sum',
            'травмы': 'sum'
        })
        
        previous_data = df[df['год'] == previous_year].groupby('район').agg({
            'количество_пожаров': 'count',
            'погибло': 'sum',
            'травмы': 'sum'
        })
        
        if not current_data.empty and not previous_data.empty:
            comparison = pd.DataFrame({
                'текущий_год_пожары': current_data['количество_пожаров'],
                'прошлый_год_пожары': previous_data['количество_пожаров'],
                'текущий_год_погибло': current_data['погибло'],
                'прошлый_год_погибло': previous_data['погибло'],
                'текущий_год_травмы': current_data['травмы'],
                'прошлый_год_травмы': previous_data['травмы']
            }).fillna(0)
            
            comparison['изменение_пожаров'] = comparison['текущий_год_пожары'] - comparison['прошлый_год_пожары']
            comparison['изменение_пожаров_%'] = (comparison['изменение_пожаров'] / comparison['прошлый_год_пожары'] * 100).round(1)
            comparison['изменение_погибло'] = comparison['текущий_год_погибло'] - comparison['прошлый_год_погибло']
            comparison['изменение_травмы'] = comparison['текущий_год_травмы'] - comparison['прошлый_год_травмы']
            
            st.write(f"**Сравнение {current_year} года с {previous_year} годом:**")
            
            # Показываем общие итоги
            col1, col2, col3 = st.columns(3)
            with col1:
                total_fires_change = comparison['изменение_пожаров'].sum()
                st.metric("Изменение количества пожаров", 
                         f"{comparison['текущий_год_пожары'].sum():.0f}",
                         f"{total_fires_change:+.0f}")
            with col2:
                total_deaths_change = comparison['изменение_погибло'].sum()
                st.metric("Изменение количества погибших",
                         f"{comparison['текущий_год_погибло'].sum():.0f}",
                         f"{total_deaths_change:+.0f}")
            with col3:
                total_injuries_change = comparison['изменение_травмы'].sum()
                st.metric("Изменение количества пострадавших",
                         f"{comparison['текущий_год_травмы'].sum():.0f}",
                         f"{total_injuries_change:+.0f}")
            
            st.dataframe(comparison, use_container_width=True)
        else:
            st.info("Недостаточно данных для сравнения АППГ")
    else:
        st.info("Отсутствуют данные для сравнения АППГ")

def predict_fire_trend(df):
    """Прогноз тенденций пожаров"""
    st.subheader("Прогноз тенденций пожаров")
    
    if 'год' in df.columns:
        yearly_stats = df.groupby('год').agg({
            'количество_пожаров': 'count'
        }).reset_index()
        
        if len(yearly_stats) > 1:
            current_year = yearly_stats.iloc[-1]
            previous_year = yearly_stats.iloc[-2]
            
            fires_trend = "📈 Растущая" if current_year['количество_пожаров'] > previous_year['количество_пожаров'] else "📉 Снижающаяся"
            fires_change = ((current_year['количество_пожаров'] - previous_year['количество_пожаров']) / previous_year['количество_пожаров'] * 100)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="Тренд пожаров",
                    value=fires_trend,
                    delta=f"{fires_change:.1f}%"
                )
            
            with col2:
                # Простой прогноз
                if len(yearly_stats) > 2:
                    avg_growth = yearly_stats['количество_пожаров'].pct_change().mean()
                    next_year_pred = current_year['количество_пожаров'] * (1 + avg_growth)
                    st.metric(
                        label="Прогноз на след. год",
                        value=f"{next_year_pred:.0f} пожаров",
                        delta=f"{avg_growth*100:.1f}%"
                    )
        else:
            st.info("Недостаточно данных для прогноза (нужно минимум 2 года)")
    else:
        st.info("Отсутствуют данные для прогноза")

# Основное приложение
def main():
    st.title("🔥 Аналитический дашборд пожаров")
    
    # Загрузка файла
    st.sidebar.header("Загрузка данных")
    uploaded_file = st.sidebar.file_uploader("Загрузите Excel файл с данными о пожарах", 
                                           type=['xlsx', 'xls'])
    
    if uploaded_file is not None:
        df = load_data(uploaded_file)
        
        if df is not None:
            st.sidebar.success(f"Данные загружены: {len(df)} записей")
            
            # Показываем информацию о данных
            with st.expander("📊 Информация о загруженных данных"):
                st.write(f"**Всего записей:** {len(df)}")
                st.write(f"**Период данных:** {df['год'].min()} - {df['год'].max()}")
                if 'район' in df.columns:
                    st.write(f"**Количество районов:** {df['район'].nunique()}")
                
                # Информация о причинах
                if 'причина_очищенная' in df.columns:
                    cause_stats = df['причина_очищенная'].value_counts()
                    st.write("**Распределение причин:**")
                    for cause, count in cause_stats.items():
                        st.write(f"- {cause}: {count} ({count/len(df)*100:.1f}%)")
                
                st.write("**Первые 5 записей:**")
                st.dataframe(df.head(), use_container_width=True)
            
            # Аналитические разделы
            analyze_fire_trends(df)  # 1. Динамика по годам
            st.divider()
            
            analyze_district_distribution(df)  # 2.1 Рейтинг районов
            analyze_district_map(df)  # 2.2 Карта районов
            st.divider()
            
            analyze_causes(df)  # 3. Причины пожаров
            st.divider()
            
            analyze_locations(df)  # 4. Места возникновения
            st.divider()
            
            analyze_seasonality(df)  # 5. Сезонность
            st.divider()
            
            analyze_district_dynamics(df)  # 6. Динамика по районам
            st.divider()
            
            analyze_comparison(df)  # 7. Сравнение АППГ
            st.divider()
            
            predict_fire_trend(df)  # Прогноз
            
    else:
        st.info("👆 Пожалуйста, загрузите Excel файл с данными о пожарах для начала анализа")

if __name__ == "__main__":
    main()