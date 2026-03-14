import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import os
import json
import base64
from io import BytesIO
from datetime import datetime
import random
import re

# --- 1. CONFIGURATION & STATE ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 🌟 绝对路径锁定素材库
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets_cozy")
CAT_ICON_PATH = os.path.join(BASE_DIR, "cat_model.png") 

if 'observer_log' not in st.session_state:
    st.session_state['observer_log'] = []
if 'latest_card' not in st.session_state:
    st.session_state['latest_card'] = None

def get_available_assets():
    manifest = {}
    if not os.path.exists(ASSET_DIR): 
        return manifest
    for folder in os.listdir(ASSET_DIR):
        path = os.path.join(ASSET_DIR, folder)
        if os.path.isdir(path):
            # 🌟 修复: 兼容 .PNG 和 .png
            manifest[folder] = [f for f in os.listdir(path) if f.lower().endswith('.png')]
    return manifest

def img_to_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def get_mbti_colors(mbti_str):
    mbti_str = str(mbti_str).strip().upper()
    match = re.search(r'[IE][NS][TF][JP]', mbti_str)
    core = match.group(0) if match else mbti_str

    if core in ["INTJ", "INTP", "ENTJ", "ENTP"]: 
        return {"bg": "#8B7DB3", "border": "#5B4A80", "stat": "#6B5A90", "story_bg": "#F4F2F8"}
    elif core in ["INFJ", "INFP", "ENFJ", "ENFP"]: 
        return {"bg": "#7B9E83", "border": "#486950", "stat": "#557A5D", "story_bg": "#F2F6F3"}
    elif core in ["ISTP", "ISFP", "ESTP", "ESFP"]: 
        return {"bg": "#C0A068", "border": "#8C6C38", "stat": "#A38048", "story_bg": "#F9F6F0"}
    elif core in ["ISTJ", "ISFJ", "ESTJ", "ESFJ"]: 
        return {"bg": "#6B82B8", "border": "#4A5A80", "stat": "#465A8C", "story_bg": "#F2F4F8"}
    else: 
        return {"bg": "#6B82B8", "border": "#4A5A80", "stat": "#465A8C", "story_bg": "#F2F4F8"}

# --- 2. PIXEL SCENE RENDERER ---
def build_npc_image(npc_list, background_choice):
    BG_W, BG_H = 384, 256 
    canvas = Image.new("RGBA", (BG_W, BG_H), (107, 130, 184, 255))
    
    if not background_choice or background_choice == "none":
        background_choice = "general.png"
    elif not background_choice.endswith('.png'):
        background_choice += ".png"
        
    bg_path = os.path.join(ASSET_DIR, 'backgrounds', background_choice)
    if not os.path.exists(bg_path):
        bg_path = os.path.join(ASSET_DIR, 'backgrounds', 'general.png')

    if os.path.exists(bg_path):
        bg_img = Image.open(bg_path).convert("RGBA")
        bg_img = bg_img.resize((BG_W, BG_H), resample=Image.NEAREST)
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=1.2))
        enhancer = ImageEnhance.Color(bg_img)
        bg_img = enhancer.enhance(0.7) 
        overlay = Image.new("RGBA", bg_img.size, (0, 0, 0, 60)) 
        bg_img = Image.alpha_composite(bg_img, overlay)
        canvas.paste(bg_img, (0, 0))

    char_scale = 6 
    char_size = 32 * char_scale 
    
    if not isinstance(npc_list, list) or len(npc_list) == 0:
        npc_list = [{}] 
        
    num_npcs = len(npc_list)
    available_assets = get_available_assets()

    for idx, npc_assets in enumerate(npc_list):
        sprite_canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        layer_order = ['body', 'pants', 'shoes', 'clothes', 'outfit', 'hair', 'blush', 'lipstick', 'props', 'pet', 'status']
        
        for layer in layer_order:
            filename = npc_assets.get(layer)
            
            if layer in ['body', 'clothes', 'hair'] and idx == 0:
                if not filename or filename == "none" or filename not in available_assets.get(layer, []):
                    if layer == 'body' and 'light - default face 1 .png' in available_assets.get('body', []):
                        filename = 'light - default face 1 .png'
                    elif available_assets.get(layer):
                        filename = available_assets[layer][0] 
                        
            if filename and filename != "none":
                if idx == 0 and layer == 'props':
                    continue
                
                path = os.path.join(ASSET_DIR, layer, filename)
                if os.path.exists(path):
                    img = Image.open(path).convert("RGBA")
                    
                    if layer == 'status':
                        small_bubble = img.resize((14, 14), resample=Image.NEAREST)
                        sprite_canvas.paste(small_bubble, (16, 0), small_bubble)
                    
                    elif layer == 'blush':
                        temp_layer = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
                        temp_layer.paste(img, (0, -1)) 
                        sprite_canvas.alpha_composite(temp_layer)
                    elif layer == 'lipstick':
                        sprite_canvas.alpha_composite(img)
                        
                    elif layer == 'pet':
                        pet_w, pet_h = img.size
                        new_w, new_h = int(pet_w * 0.85), int(pet_h * 0.85)
                        img = img.resize((new_w, new_h), resample=Image.NEAREST)
                        temp_layer = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
                        temp_layer.paste(img, ((32 - new_w) // 2, 32 - new_h))
                        sprite_canvas.alpha_composite(temp_layer)
                    else:
                        if layer == 'hair':
                            temp_layer = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
                            temp_layer.paste(img, (0, -1)) 
                            sprite_canvas.alpha_composite(temp_layer)
                        else:
                            sprite_canvas.alpha_composite(img)
        
        scaled_sprite = sprite_canvas.resize((char_size, char_size), resample=Image.NEAREST)
        
        if num_npcs == 1:
            char_x = (BG_W - char_size) // 2
        else:
            offset = -90 if idx == 0 else 90 
            char_x = ((BG_W - char_size) // 2) + offset
            
        char_y = BG_H - char_size - 12
        canvas.alpha_composite(scaled_sprite, dest=(char_x, char_y))
    
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, BG_W-1, BG_H-1], outline=(62, 77, 112, 255), width=6)
    
    return canvas

# --- 3. THE AI BRAIN ---
def analyze_human_log(where, moment, guess):
    manifest = get_available_assets()
    
    prompt = f"""
    你是一个毒舌、犀利且极其理性的福尔摩斯。你的目标是理解和解剖人类。
    场景: {where} | 画面: "{moment}" | 猜测: "{guess}"
    
    🔥 关键规则 (CRITICAL):
    1. 🌐 **双语自适应**:
       - 如果用户的输入 (画面描述或猜测) 主要是英文，请使用 **全英文** 返回所有的文案 (summary_name, summary_story, song, labels 等)。
       - 此时你的语气必须是 cynical British Sherlock-style English。
       - 如果输入主要是中文，则保持中文吐槽文案输出。
       - "ui_lang": 返回 "EN" 或 "CN"，指示当前卡片UI语言。
    2. 🚫 **Body即灵魂 (最重要)**: 
       - `body` 文件夹包含了肤色和眼睛表情！请根据画面的情绪挑选最匹配的 body 文件。
       - 默认优先选名字带 `light` 的文件。如果人物生气选 `light - angry face.png`。
    3. 🚫 绝对严禁裸奔: 人类 NPC 的 `body`, `lipstick`, `clothes`, `pants`, `hair` 必须**全部**从 manifest 中选择有效文件名！找不到完全匹配的就找最接近的。
    4. 🎨 视觉规则: 人类 NPC 的 `props` 默认填 "none"。
       - 特例：🌟 问题 6：如果用户的 Prompt 中明确提到 "烟" (smoke/cigarette)，AI 必须在 Manifest 的 `props` 文件夹中搜索包含这些英文特征的文件名 (例如，`smoke.png`)。如果找到，必须分配它给主角 npc (npcs[0])。如果没有找到，必须将道具文字包含在故事中，将 props 设为 "none"。提到的食物道具也要应用此逻辑。
       - 如果有宠物，单独拆分为一个 npc 对象。
    5. 🕵️ 灵魂文案: 
       - 英文模式: Use sharp, sophisticated, British Sherlock-style cynical English.
       - 中文模式: 保持尖酸刻薄但理性的“高逼格”吐槽。
       - 字数限制: 🌟 问题 4：最大字数限制为 50-80 字 (或同等长度单词)。绝不能超出。
    6. "summary_name": 起一个有故事感的名字。
    7. 颜色匹配优先: 提到“黑色”，优先找文件名带 black, dark 的。
    8. 除非提到“墨镜”或“眼镜”，否则不要选墨镜。
    9. "Regardless of the input language, always map descriptions to the most relevant English filenames in the manifest."
    10. 【critical】当场景promp输入“土土生日快乐”，务必生成一只黑色小猫，一颗爱心prop，一个快乐的女孩，在home的background。文案：“天下第二可爱完美的小猫每天都快乐哟！”
    11. 【critical】当场景prompt输入“小尾巴”，务必生成两个快乐的女孩，中间一个爱心的prop 在home的background。文案：“小尾巴❤️❤️❤️呼呼”。
    
    FILES: {json.dumps(manifest)}
    
    返回 STRICT JSON:
    {{
      "ui_lang": "CN",
      "summary_name": "...", 
      "summary_story": "...", 
      "energy": 0-100, "charm": 0-100, "capacity": 0-100, "cuteness": 0-100,
      "mbti": "...", 
      "song": "Song Title - Artist",
      "background_choice": "...",
      "npcs": [ {{ "body": "...", "clothes": "...", "outfit": "...", "pants": "...", "shoes": "...", "hair": "...", "props": "...", "pet": "...", "status": "..." }} ]
    }}
    """
    
    response = model.generate_content(
        prompt, 
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.8
        )
    )
    
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:-3].strip()
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:-3].strip()
    return json.loads(raw_text)

# --- 4. THE HTML CARD GENERATOR ---
def generate_card_html(log):
    img_b64 = img_to_base64(log['img'])
    c = get_mbti_colors(log.get('mbti')) 
    
    is_en = log.get('ui_lang', 'CN') == 'EN'
    l_energy = "Energy" if is_en else "能量"
    l_charm = "Charm" if is_en else "魅力"
    l_capacity = "Appetite" if is_en else "饭量"
    l_cute = "Cuteness" if is_en else "可爱"
    l_story = "HIDDEN BACKSTORY:" if is_en else "隐藏故事:"
    l_location = log.get('geo_location', 'Unknown') if is_en else log.get('geo_location', '未知坐标')
    
    return f"""
    <div class="pixel-card" style="background-color: {c['bg']}; border-color: {c['border']}; box-shadow: 6px 6px 0px {c['border']};">
        <div class="card-header">
            <div class="card-title" title="{log.get('name', '')}">{log.get('name', '')}</div>
            <div class="card-subtitle">{log.get('mbti', '')}</div> 
        </div>
        <div class="card-middle">
            <img src="data:image/png;base64,{img_b64}" class="card-image" style="border-color: {c['border']};">
            <div class="card-stats">
                <div class="stat-box" style="background-color: {c['stat']}; border-color: {c['border']};"><span>{l_energy}</span><span>{log.get('energy', 50)}</span></div>
                <div class="stat-box" style="background-color: {c['stat']}; border-color: {c['border']};"><span>{l_charm}</span><span>{log.get('charm', 50)}</span></div>
                <div class="stat-box" style="background-color: {c['stat']}; border-color: {c['border']};"><span>{l_capacity}</span><span>{log.get('capacity', 50)}</span></div>
                <div class="stat-box" style="background-color: {c['stat']}; border-color: {c['border']};"><span>{l_cute}</span><span>{log.get('cuteness', 50)}</span></div>
            </div>
        </div>
        <div class="card-story" style="background-color: {c['story_bg']}; border-color: {c['border']};">
            <div class="story-label">{l_story}</div>
            {log.get('story', '')}
        </div>
        <div class="card-song">🎵 {log.get('song', '')}</div>
        <div class="card-location">📍 {l_location}</div>
    </div>
    """

# --- 5. THE UI ---
page_icon_img = Image.open(CAT_ICON_PATH) if os.path.exists(CAT_ICON_PATH) else "👾"
st.set_page_config(page_title="人类捕捉器", page_icon=page_icon_img, layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@500;700;900&display=swap');
* { font-family: 'Noto Sans SC', sans-serif !important; }
.stApp { background-color: #E7EDF6 !important; }
h1, h2, h3, p, label, span, div { color: #2D3748 !important; }
label p { font-weight: 900 !important; }
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #94A3B8 !important; opacity: 1 !important; }
.block-container { background-color: #FFFFFF !important; border: 4px solid #B0C4DE !important; border-radius: 12px !important; padding: 2rem !important; }
[data-testid="stVerticalBlock"] > [data-testid="column"] { background-color: #F4F7FB !important; border: 3px solid #DDE2EC !important; border-radius: 8px !important; padding: 15px !important; }

/* 🌟 修复: basWeb 改成 baseweb，并强制文字颜色为深色 */
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #2D3748 !important; border: 2px solid #94A3B8 !important; border-radius: 4px !important; -webkit-text-fill-color: #2D3748 !important;}
div[data-baseweb="popover"] > div, ul[role="listbox"] { background-color: #FFFFFF !important; }
ul[role="listbox"] li { color: #2D3748 !important; font-weight: bold !important; }

button[data-testid="baseButton-primary"] { background-color: #4A5A80 !important; border: 2px solid #2D3748 !important; box-shadow: 4px 4px 0px #2D3748 !important; }
button[data-testid="baseButton-primary"] * { color: #FFFFFF !important; font-weight: 900 !important; font-size: 18px !important; }

.pixel-card { 
    border-radius: 4px; 
    width: 100%; 
    max-width: 360px; 
    min-height: 600px; 
    height: auto !important; 
    margin: 10px auto; 
    border-style: solid; 
    border-width: 4px;
    display: flex;
    flex-direction: column;
}
.card-header { text-align: center; padding: 15px 10px 5px; }
.card-title { font-size: 24px; font-weight: 900; letter-spacing: 2px; color: #FFFFFF !important; text-shadow: 2px 2px 0px rgba(0,0,0,0.3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.card-subtitle { font-size: 18px; font-weight: 900; letter-spacing: 1px; color: rgba(255,255,255,0.95) !important; margin-top: -2px;}
.card-middle { display: flex; flex-direction: column; padding: 0 15px 5px 15px; gap: 10px; align-items: center; }
.card-image { width: 100%; border-style: solid; border-width: 3px; border-radius: 4px; background-color: #A3B8D7; image-rendering: pixelated; }
.card-stats { width: 100%; display: flex; flex-direction: column; gap: 4px; }
.stat-box { padding: 4px 12px; border-radius: 4px; display: flex; justify-content: space-between; border-style: solid; border-width: 2px; }
.stat-box span { font-size: 14px; font-weight: 900; color: #FFFFFF !important; }
.card-story { color: #333333 !important; margin: 0 15px 10px 15px; padding: 12px; border-radius: 4px; border-style: solid; border-width: 3px; font-size: 14px; font-weight: 700; line-height: 1.5; height: auto !important; min-height: 100px;}
.story-label { font-size: 11px; color: #888888 !important; margin-bottom: 4px; text-transform: uppercase; }
.card-song { margin-top: auto; text-align: center; font-size: 12px; padding-bottom: 4px; color: rgba(255,255,255,0.85) !important; font-weight: bold; }
.card-location { text-align: center; font-size: 12px; padding-bottom: 12px; color: rgba(255,255,255,0.7) !important; font-weight: bold; }
@media (max-width: 768px) { .block-container { padding: 1rem 0.5rem !important; border: none !important; } .pixel-card { max-width: 100%; margin: 5px 0; } }
[data-testid="stExpander"] { border: 2px solid #B0C4DE !important; border-radius: 8px !important; margin-top: 10px;}
[data-testid="stExpander"] p { font-size: 13px !important; }
</style>
""", unsafe_allow_html=True)

if os.path.exists(CAT_ICON_PATH):
    cat_b64 = img_to_base64(Image.open(CAT_ICON_PATH))
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px;">
        <img src="data:image/png;base64,{cat_b64}" style="width: 48px; height: 48px; image-rendering: pixelated; margin-bottom: 10px;">
        <h1 style="margin: 0; padding: 0;">人类捕捉器</h1>
    </div>
    """, unsafe_allow_html=True)
else:
    st.title(" 🤖 人类捕捉器")

st.markdown("**谁让你今天多瞅了两眼？**")

tab_log, tab_collection = st.tabs(["🐾 今日人类", "🗂️ 我的图鉴"])

with tab_log:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col1:
        where_input = st.selectbox("📍 场景:", ("街道", "室内", "交通工具", "公园", "随机"), key="input_where")
        date_input = st.text_input("🕒 时间:", datetime.now().strftime("%Y-%m-%d %H:%M"), key="input_date")
        location_input = st.text_input("🌍 捕获地（城市/地点）:", placeholder="例：多伦多美术馆", key="input_loc")
        
    with col2:
        moment_input = st.text_area("👁️ 画面描述 (越详细越好):", placeholder="例：一个穿着黑风衣的短发酷女孩，牵着柯基等红灯，眉头紧锁...（试试加入动物词汇哦）", key="input_moment")
        guess_input = st.text_input("💡 你猜猜发生什么了？", placeholder="例：大概率是思考柯基的腿到底多长...", key="input_guess")
    with col3:
        st.write("")
        st.write("")
        if st.button("📸 捕捉瞬间！", type="primary"):
            if not GEMINI_API_KEY:
                st.error("🚨 请填入你的 API Key！")
            elif moment_input:
                with st.spinner("正在加载福尔摩斯系统..."):
                    try:
                        result = analyze_human_log(where_input, moment_input, guess_input)
                        img = build_npc_image(result.get('npcs', []), result.get('background_choice'))
                        
                        log_entry = {
                            "date": date_input, 
                            "location": where_input, 
                            "geo_location": location_input if location_input else "神秘坐标", 
                            "moment": moment_input, 
                            "guess": guess_input,   
                            "img": img, 
                            "name": result.get('summary_name', 'Unknown'), 
                            "story": result.get('summary_story', '...'), 
                            "energy": result.get('energy', 50), "charm": result.get('charm', 50), 
                            "capacity": result.get('capacity', 50), "cuteness": result.get('cuteness', 50),
                            "mbti": result.get('mbti', 'XXXX'), "song": result.get('song', 'None'),
                            "ui_lang": result.get('ui_lang', 'CN')
                        }
                        st.session_state['observer_log'].append(log_entry)
                        st.session_state['latest_card'] = log_entry 
                    except Exception as e:
                        st.error(f"🚨 引擎故障！(错误: {e})")
            else:
                st.warning("你说两句呢？")

    if st.session_state.get('latest_card'):
        st.divider()
        st.markdown(f"""
        <div style="display: flex; justify-content: center; width: 100%;">
            {generate_card_html(st.session_state['latest_card'])}
        </div>
        """, unsafe_allow_html=True)

with tab_collection:
    if not st.session_state['observer_log']:
        st.info("图鉴空空如也。去捕捉第一个人类吧！")
    else:
        sorted_logs = sorted(st.session_state['observer_log'], key=lambda x: x['date'], reverse=True)
        cols = st.columns(3)
        for i, log in enumerate(sorted_logs):
            with cols[i % 3]:
                st.markdown(generate_card_html(log), unsafe_allow_html=True)
                with st.expander("📜 查看你的观察日记"):
                    st.markdown(f"**👁️ 当时画面:** {log.get('moment', '无')}")
                    st.markdown(f"**💡 我的脑洞:** {log.get('guess', '无')}")
