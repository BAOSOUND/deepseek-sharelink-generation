import streamlit as st

st.set_page_config(page_title="测试导入")

st.title("模块导入测试")

# 测试导入 auto_deepseek
try:
    from auto_deepseek import DeepSeekAuto
    st.success("✅ auto_deepseek 导入成功")
    st.write("DeepSeekAuto 类型:", type(DeepSeekAuto))
except Exception as e:
    st.error(f"❌ 导入失败: {e}")
    import traceback
    st.code(traceback.format_exc())

# 测试 playwright
try:
    from playwright.async_api import async_playwright
    st.success("✅ playwright 导入成功")
except Exception as e:
    st.error(f"❌ playwright 导入失败: {e}")
