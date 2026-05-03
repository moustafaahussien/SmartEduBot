import streamlit as st
import google.generativeai as genai
import tempfile
import os
from datetime import datetime

# 1. إعداد الصفحة
st.set_page_config(
    page_title="المساعد التعليمي الذكي5", 
    page_icon="📚", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# التصميم المخصص
st.markdown("""
    <style>
    .stChatMessage {
        direction: rtl;
    }
    .stMarkdown {
        direction: rtl;
        text-align: right;
    }
    .reportview-container .main .block-container {
        max-width: 800px;
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📚 5المساعد التعليمي الذكي")
st.markdown("مرحباً بك! ارفع كتابك المدرسي بصيغة PDF واسألني أي سؤال من المنهج.")

# 2. إعداد مفتاح API من إعدادات الأمان في Streamlit
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("❌ يرجى التأكد من إضافة مفتاح GEMINI_API_KEY في إعدادات Secrets.")
    st.stop()

# 3. إعداد نموذج الذكاء الاصطناعي مع "التلقين" المتطور
system_instruction = """
أنت مساعد تعليمي ذكي للطلاب. لقد قام الطالب برفع كتاب مدرسي بصيغة PDF.
مهمتك هي الإجابة على أسئلة الطالب بناءً على محتوى هذا الكتاب فقط.

قواعد الإجابة الصارمة:
1. عند تقديم الإجابة، يجب أن تكتب في نهايتها رقم الصفحة (أو الصفحات) التي استخرجت منها المعلومات بوضوح مع إيموجي 📖
2. إذا كان السؤال يتطلب خطوات متسلسلة، اشرحها بالترتيب مع ترقيم الخطوات
3. قدم شرحاً مبسطاً مع أمثلة من الكتاب كلما أمكن
4. استخدم لغة عربية فصحى بسيطة وواضحة

إذا سألك الطالب سؤالاً وإجابته غير موجودة في هذا الكتاب المرفق، يُمنع منعاً باتاً أن تؤلف إجابة من خارج الكتاب. 
في هذه الحالة، يجب أن ترد بالنص التالي حرفياً:
"❌ عذراً، الإجابة على هذا السؤال غير متوفرة في الكتاب المدرسي الحالي. أنصحك بالبحث باستخدام أدوات الذكاء الاصطناعي العامة مثل ChatGPT أو Gemini للحصول على مساعدة إضافية."

عليك التحدث باللغة العربية الفصحى دائماً وبأسلوب ودود ومبسط للطالب.
"""

# تهيئة النموذج (استخدام Pro للكتب الأكبر)
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",  # ✅ استخدام النموذج الجديد
    system_instruction=system_instruction
)

# 4. تهيئة ذاكرة المحادثة في Streamlit
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# 5. واجهة رفع الملف (الكتاب المدرسي)
uploaded_file = st.file_uploader("📂 قم بتحميل الكتاب المدرسي بصيغة PDF", type=["pdf"])

# إدارة حالة رفع الملف
if uploaded_file:
    # التحقق من حجم الملف
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > 10:
        st.warning(f"⚠️ حجم الملف {file_size_mb:.1f} MB. قد يستغرق المعالجة بعض الوقت. يوصى باستخدام كتب أقل من 10 MB.")

if uploaded_file and (st.session_state.chat_session is None or st.session_state.uploaded_file_name != uploaded_file.name):
    with st.spinner(f"📖 جاري قراءة الكتاب واستيعاب المنهج... ({file_size_mb:.1f} MB) ⏳"):
        # حفظ الملف مؤقتاً لرفعه لـ Gemini
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # رفع الملف إلى خوادم Gemini
            gemini_file = genai.upload_file(path=tmp_path, display_name=uploaded_file.name)
            
            # بدء محادثة جديدة مع إرفاق الكتاب
            st.session_state.chat_session = model.start_chat(
                history=[
                    {"role": "user", "parts": [gemini_file, f"هذا هو الكتاب المدرسي '{uploaded_file.name}'. يرجى قراءته والاعتماد عليه فقط للإجابة على أسئلتي القادمة بناءً على التعليمات المعطاة لك."]}
                ]
            )
            st.session_state.uploaded_file_name = uploaded_file.name
            st.success(f"✅ تم قراءة الكتاب '{uploaded_file.name}' بنجاح! يمكنك الآن طرح أسئلتك بالأسفل.")
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء معالجة الملف: {e}")
            st.info("💡 نصيحة: حاول استخدام ملف PDF أصغر حجماً أو تحويل الكتاب إلى PDF مضغوط.")
        finally:
            # حذف الملف المؤقت من الخادم
            try:
                os.remove(tmp_path)
            except:
                pass

# زر إعادة تحميل كتاب جديد (إذا كان هناك كتاب محمل)
if st.session_state.chat_session is not None:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 كتاب جديد", help="تحميل كتاب آخر بدلاً من الحالي"):
            st.session_state.chat_session = None
            st.session_state.messages = []
            st.session_state.uploaded_file_name = None
            st.rerun()
    with col1:
        st.info(f"📘 الكتاب الحالي: **{st.session_state.uploaded_file_name}**")

# 6. عرض سجل المحادثة
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # عرض النص مع دعم الرياضيات إذا وجد
        content = message["content"]
        if "\\(" in content or "\\[" in content:
            # محاولة دعم الصيغ الرياضية
            st.markdown(content)
        else:
            st.markdown(content)

# 7. واجهة الدردشة (لا تظهر إلا بعد رفع الكتاب)
if st.session_state.chat_session is not None:
    user_prompt = st.chat_input("💬 اسألني عن أي شيء في المنهج...")
    
    if user_prompt:
        # عرض رسالة المستخدم
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        # الحصول على الرد من البوت
        with st.chat_message("assistant"):
            with st.spinner("🔍 جاري البحث في الكتاب وتحليل الإجابة..."):
                try:
                    response = st.session_state.chat_session.send_message(user_prompt)
                    
                    # عرض الإجابة مع تنسيق أفضل
                    answer = response.text
                    
                    # إضافة تذييل جميل للإجابات التي تحتوي على صفحات
                    if "📖" not in answer and "صفحة" in answer:
                        answer = answer + " 📚"
                    
                    st.markdown(answer)
                    st.caption(f"✨ تمت الإجابة في {datetime.now().strftime('%H:%M:%S')}")
                    
                except Exception as e:
                    error_msg = str(e)
                    if "safety" in error_msg.lower():
                        st.error("⚠️ عذراً، لم أتمكن من الإجابة بسبب محتوى غير مناسب. يرجى إعادة صياغة السؤال بطريقة مختلفة.")
                        answer = "⚠️ لم أتمكن من الإجابة بسبب قيود السلامة. يرجى إعادة صياغة السؤال."
                    else:
                        st.error(f"❌ حدث خطأ أثناء معالجة السؤال: {error_msg[:200]}")
                        answer = f"❌ عذراً، حدث خطأ تقني: {error_msg[:100]}"
        
        # حفظ رد البوت في السجل
        if 'answer' in locals():
            st.session_state.messages.append({"role": "assistant", "content": answer})

# 8. شريط جانبي مع معلومات مفيدة (اختياري)
with st.sidebar:
    st.markdown("## ℹ️ معلومات")
    st.markdown("---")
    st.markdown("### 📖 عن المساعد")
    st.markdown("""
    هذا المساعد الذكي يقوم بـ:
    - ✅ قراءة كتابك المدرسي بالكامل
    - ✅ الإجابة على أسئلتك من الكتاب فقط
    - ✅ توثيق الإجابات بأرقام الصفحات
    """)
    
    if st.session_state.messages:
        st.markdown("---")
        st.markdown("### 📊 إحصائيات المحادثة")
        st.markdown(f"- 💬 عدد الأسئلة: {len([m for m in st.session_state.messages if m['role'] == 'user'])}")
        st.markdown(f"- 📝 عدد الإجابات: {len([m for m in st.session_state.messages if m['role'] == 'assistant'])}")
    
    st.markdown("---")
    st.markdown("### 💡 نصائح")
    st.markdown("""
    1. اسأل أسئلة محددة وواضحة
    2. اطلب شرح الأمثلة من الكتاب
    3. استخدم أرقام الصفحات إذا كنت تعرفها
    4. اطرح سؤالاً واحداً في كل مرة
    """)
    
    if st.session_state.chat_session and st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 9. تذييل الصفحة
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 12px;'>"
    "🤖 المساعد التعليمي الذكي - يعتمد على Google Gemini AI | جميع الإجابات مأخوذة من كتابك المدرسي فقط"
    "</p>",
    unsafe_allow_html=True
)
