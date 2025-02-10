import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("Карта доставки по штатам США")
with st.expander("Описание работы приложения"):
    st.markdown("""
    **Описание цветов:**
    - **Синий:** 0–2 дня доставки – максимально быстрая доставка.
    - **Зеленый:** 3 дня доставки.
    - **Желтый:** 4 дня доставки.
    - **Оранжевый:** 5–6 дней доставки.
    - **Красный:** 7 и более дней доставки – наименее быстрая доставка.
  
    **Как работает карта:**
    - Приложение ожидает загрузку CSV-файла с тремя столбцами:
        - **state_from:** штат, откуда отправляется груз (склад);
        - **state_to:** штат, куда идёт доставка;
        - **time_dalivery:** время доставки в днях (целое число).
    - По умолчанию выбираются все склады (значения из колонки `state_from`), и для каждого штата назначения (`state_to`) определяется минимальное время доставки из выбранных складов.
    - Каждый штат на карте окрашивается в цвет, соответствующий минимальному времени доставки:
        - Если время доставки отсутствует – штат остаётся **белым**.
        - Если время доставки 0–2 дня – штат окрашивается **синим**.
        - Если время доставки 3 дня – штат окрашивается **зеленым**.
        - Если время доставки 4 дня – штат окрашивается **желтым**.
        - Если время доставки 5–6 дней – штат окрашивается **оранжевым**.
        - Если время доставки 7 и более дней – штат окрашивается **красным**.
    - На боковой панели можно выбрать, какие склады (значения из `state_from`) участвуют в расчётах. По умолчанию выбраны все.
    - На карте также отображаются метки складов (иконки-звёзды):
        - **Зеленая звезда:** склад выбран в фильтре.
        - **Серая звезда:** склад не выбран.
    - При наведении курсора на штат появляется подсказка с названием штата и информацией о минимальном времени доставки.
    """)

# Функция для определения цвета по времени доставки
def get_color(time):
    if time is None:
        return 'white'
    elif time <= 2:
        return 'blue'
    elif time == 3:
        return 'green'
    elif time == 4:
        return 'yellow'
    elif 5 <= time <= 6:
        return 'orange'
    elif time >= 7:
        return 'red'
    return 'white'

# Кэшируем загрузку GeoJSON с границами штатов
@st.cache_data
def load_geojson():
    url = 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json'
    response = requests.get(url)
    return response.json()

us_states_geojson = load_geojson()

# Словарь с координатами (примерные центры штатов) для нанесения меток складов и отображения заказов.
state_centers = {
    "Alabama": [32.806671, -86.791130],
    "Alaska": [61.370716, -152.404419],
    "Arizona": [33.729759, -111.431221],
    "Arkansas": [34.969704, -92.373123],
    "California": [36.116203, -119.681564],
    "Colorado": [39.059811, -105.311104],
    "Connecticut": [41.597782, -72.755371],
    "Delaware": [39.318523, -75.507141],
    "Florida": [27.766279, -81.686783],
    "Georgia": [33.040619, -83.643074],
    "Hawaii": [21.094318, -157.498337],
    "Idaho": [44.240459, -114.478828],
    "Illinois": [40.349457, -88.986137],
    "Indiana": [39.849426, -86.258278],
    "Iowa": [42.011539, -93.210526],
    "Kansas": [38.526600, -96.726486],
    "Kentucky": [37.668140, -84.670067],
    "Louisiana": [31.169546, -91.867805],
    "Maine": [44.693947, -69.381927],
    "Maryland": [39.063946, -76.802101],
    "Massachusetts": [42.230171, -71.530106],
    "Michigan": [43.326618, -84.536095],
    "Minnesota": [45.694454, -93.900192],
    "Mississippi": [32.741646, -89.678696],
    "Missouri": [38.456085, -92.288368],
    "Montana": [46.921925, -110.454353],
    "Nebraska": [41.125370, -98.268082],
    "Nevada": [38.313515, -117.055374],
    "New Hampshire": [43.452492, -71.563896],
    "New Jersey": [40.298904, -74.521011],
    "New Mexico": [34.840515, -106.248482],
    "New York": [42.165726, -74.948051],
    "North Carolina": [35.630066, -79.806419],
    "North Dakota": [47.528912, -99.784012],
    "Ohio": [40.388783, -82.764915],
    "Oklahoma": [35.565342, -96.928917],
    "Oregon": [44.572021, -122.070938],
    "Pennsylvania": [40.590752, -77.209755],
    "Rhode Island": [41.680893, -71.511780],
    "South Carolina": [33.856892, -80.945007],
    "South Dakota": [44.299782, -99.438828],
    "Tennessee": [35.747845, -86.692345],
    "Texas": [31.054487, -97.563461],
    "Utah": [40.150032, -111.862434],
    "Vermont": [44.045876, -72.710686],
    "Virginia": [37.769337, -78.169968],
    "Washington": [47.400902, -121.490494],
    "West Virginia": [38.491226, -80.954453],
    "Wisconsin": [44.268543, -89.616508],
    "Wyoming": [42.755966, -107.302490]
}

st.sidebar.header("Фильтры")

# Загрузка основного CSV-файла с данными о доставке
uploaded_file = st.file_uploader("Загрузите CSV файл", type=["csv"])
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Ошибка при чтении CSV файла: {e}")
    else:
        # Проверяем наличие необходимых колонок
        required_columns = {'state_from', 'state_to', 'time_dalivery'}
        if not required_columns.issubset(df.columns):
            st.error(f"CSV файл должен содержать колонки: {', '.join(required_columns)}")
        else:
            st.subheader("Исходные данные")
            st.dataframe(df)

            # Формируем список всех складов (state_from)
            warehouses = sorted(df['state_from'].unique())
            selected_warehouses = st.sidebar.multiselect(
                "Выберите склады (state_from):",
                options=warehouses,
                default=warehouses
            )

            # Логика расчёта минимального времени доставки для каждого штата (state_to)
            if len(selected_warehouses) == 0:
                state_min_delivery = {}
            else:
                filtered_df = df[df['state_from'].isin(selected_warehouses)]
                group = filtered_df.groupby('state_to')['time_dalivery'].min()
                state_min_delivery = group.to_dict()

            # Для каждого штата из GeoJSON задаём цвет и текст всплывающей подсказки
            state_colors = {}
            state_tooltips = {}
            for feature in us_states_geojson['features']:
                state_name = feature['properties']['name']
                min_time = state_min_delivery.get(state_name, None)
                color = get_color(min_time)
                state_colors[state_name] = color
                if min_time is not None:
                    tooltip_text = f"<b>{state_name}</b><br>Минимальное время доставки: {min_time} дн."
                else:
                    tooltip_text = f"<b>{state_name}</b><br>Нет данных"
                state_tooltips[state_name] = tooltip_text
                feature['properties']['tooltip'] = tooltip_text

            # Создаём Folium-карту, центрированную на США
            m = folium.Map(location=[37.0902, -95.7129], zoom_start=4)

            # Добавляем слой GeoJSON с раскраской штатов
            folium.GeoJson(
                us_states_geojson,
                style_function=lambda feature: {
                    'fillOpacity': 0.7,
                    'weight': 1,
                    'color': 'black',
                    'fillColor': state_colors.get(feature['properties']['name'], 'white')
                },
                tooltip=folium.features.GeoJsonTooltip(
                    fields=['tooltip'],
                    aliases=[''],
                    labels=False,
                    sticky=True
                )
            ).add_to(m)

            # Добавляем метки для складов.
            # Если склад выбран — звезда зеленая, если нет — звезда серая.
            for warehouse in warehouses:
                if warehouse in state_centers:
                    coords = state_centers[warehouse]
                    marker_color = 'green' if warehouse in selected_warehouses else 'gray'
                    folium.Marker(
                        location=coords,
                        icon=folium.Icon(icon='star', prefix='fa', color=marker_color),
                        tooltip=f"Склад: {warehouse}"
                    ).add_to(m)
                else:
                    st.warning(f"Нет координат для склада: {warehouse}")

            # --- Новый блок: загрузка CSV с количеством заказов и добавление слоя заказов с CircleMarker (по категориям) ---
            st.sidebar.header("Слой заказов")
            orders_file = st.sidebar.file_uploader("Загрузите CSV файл с количеством заказов", type=["csv"], key="orders_csv")
            show_orders_layer = st.sidebar.checkbox("Показать слой заказов", value=True)
            orders_by_state = {}
            if orders_file is not None:
                try:
                    orders_df = pd.read_csv(orders_file)
                except Exception as e:
                    st.error("Ошибка чтения CSV для заказов: " + str(e))
                else:
                    required_orders_columns = {"state_from", "state_to", "count_deliv"}
                    if not required_orders_columns.issubset(orders_df.columns):
                        st.error("CSV для заказов должен содержать колонки: " + ", ".join(required_orders_columns))
                    else:
                        st.subheader("Данные по количеству заказов")
                        st.dataframe(orders_df)
                        filtered_orders_df = orders_df[orders_df["state_from"].isin(selected_warehouses)]
                        orders_by_state = filtered_orders_df.groupby("state_to")["count_deliv"].sum().to_dict()
                        st.write("Суммарное количество заказов по штатам:", orders_by_state)

            if orders_file is not None and show_orders_layer and orders_by_state:
                orders_layer = folium.FeatureGroup(name="Заказы", show=True)
                for state, count in orders_by_state.items():
                    if state in state_centers:
                        # Определяем размер кружка по категориям
                        if count < 200:
                            radius = 5
                        elif count < 500:
                            radius = 10
                        elif count < 700:
                            radius = 15
                        elif count < 1000:
                            radius = 20
                        else:
                            radius = 25
                        popup_text = f"{state}: {count} заказов"
                        folium.CircleMarker(
                            location=state_centers[state],
                            radius=radius,
                            color='grey',
                            fill=True,
                            fill_color='grey',
                            fill_opacity=0.6,
                            popup=popup_text
                        ).add_to(orders_layer)
                orders_layer.add_to(m)
                folium.LayerControl().add_to(m)

            st.subheader("Карта доставки")
            st_data = st_folium(m, width=800, height=600)
else:
    st.info("Ожидается загрузка CSV файла.")
