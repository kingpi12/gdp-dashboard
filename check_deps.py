print("🔍 Проверка зависимостей...")

try:
    import streamlit
    print("✅ Streamlit установлен")
except ImportError:
    print("❌ Streamlit не установлен")

try:
    import pandas as pd
    print("✅ Pandas установлен")
except ImportError:
    print("❌ Pandas не установлен")

try:
    import plotly.express as px
    print("✅ Plotly установлен") 
except ImportError:
    print("❌ Plotly не установлен")

try:
    import openpyxl
    print("✅ Openpyxl установлен")
except ImportError:
    print("❌ Openpyxl не установлен")

print("\nПуть к Python:")
import sys
print(sys.executable)
