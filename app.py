import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# 1. إعداد الصفحة
st.set_page_config(page_title="المساعد التعليمي الذكي", page_icon="📚", layout="centered")
st.title("📚 المساعد التعليمي الذكي")
st.markdown("مرحباً بك! ارفع كتابك المدرسي بصيغة PDF واسألني أي سؤال من المنهج.")

# 2. إعداد مفتاح API
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("يرجى التأكد من إضافة مفتاح GEMINI_API_KEY في إعدادات Secrets.")
    st.stop()

# 3. التلقين والنموذج (تم إرجاع الاسم الأصلي الصحيح)
system_instruction = """
أنت مساعد تعليمي ذكي للطلاب. لقد قام الطالب برفع كتاب مدرسي بصيغة PDF.
مهمتك هي الإجابة على أسئلة الطالب بناءً على محتوى هذا الكتاب فقط. 
عند تقديم الإجابة، يجب أن تكتب في نهايتها رقم الصفحة (أو الصفحات) التي استخرجت منها المعلومات بوضوح.
إذا سألك الطالب سؤالاً وإجابته غير موجودة في هذا الكتاب المرفق، يُمنع منعاً باتاً أن تؤلف إجابة من خارج الكتاب. 
في هذه الحالة، يجب أن ترد بالنص التالي حرفياً: "عذراً، الإجابة على هذا السؤال غير متوفرة في الكتاب المدرسي الحالي. أنصحك بالبحث باستخدام أدوات الذكاء الاصطناعي العامة مثل ChatGPT أو Gemini للحصول على مساعدة إضافية."
عليك التحدث باللغة العربية الفصحى دائماً وبأسلوب ودود ومبسط للطالب.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", 
    system_instruction=system_instruction
)

# 4. تهيئة الذاكرة
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. واجهة رفع الملف
uploaded_file = st.file_uploader("قم بتحميل الكتاب المدرسي بصيغة PDF", type=["pdf"])

if uploaded_file and st.session_state.chat_session is None:
    with st.spinner("جاري قراءة الكتاب واستيعاب المنهج... قد يستغرق هذا بضع ثوانٍ ⏳"):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            gemini_file = genai.upload_file(path=tmp_path, display_name=uploaded_file.name)
            
            # الانتظار حتى تكتمل المعالجة في خوادم جوجل
            while gemini_file.state.name == "PROCESSING":
                time.sleep(3)
                gemini_file = genai.get_file(gemini_file.name)
            
            if gemini_file.state.name == "FAILED":
                st.error("عذراً، حدث خطأ في خوادم جوجل أثناء معالجة هذا الكتاب.")
                st.stop()
            
            # الحل الجذري: إدراج الكتاب في الذاكرة مع رد افتراضي لضبط تسلسل المحادثة
            st.session_state.chat_session = model.start_chat(
                history=[
                    {
                        "role": "user", 
                        "parts": [gemini_file, "هذا هو الكتاب المدرسي. يرجى قراءته والاعتماد عليه فقط للإجابة على أسئلتي القادمة."]
                    },
                    {
                        "role": "model", 
                        "parts": ["مفهوم. لقد قمت بقراءة الكتاب المرفق، وسأعتمد عليه حصراً في إجاباتي وسأذكر رقم الصفحة كما طلبت."]
                    }
                ]
            )
            
            st.success("✅ تم قراءة الكتاب بنجاح! يمكنك الآن طرح أسئلتك بالأسفل.")
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة الملف: {e}")
        finally:
            os.remove(tmp_path)

# 6. عرض سجل المحادثة
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 7. واجهة الدردشة
if st.session_state.chat_session is not None:
    user_prompt = st.chat_input("اسألني عن أي شيء في المنهج...")
    
    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("جاري البحث في الكتاب..."):
                try:
                    response = st.session_state.chat_session.send_message(user_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالخادم: {e}")
