import streamlit as st
import google.generativeai as genai
import tempfile
import os

# 1. إعداد الصفحة
st.set_page_config(page_title="المساعد التعليمي الذكي", page_icon="📚", layout="centered")
st.title("📚 المساعد التعليمي الذكي")
st.markdown("مرحباً بك! ارفع كتابك المدرسي بصيغة PDF واسألني أي سؤال من المنهج.")

# 2. إعداد مفتاح API من إعدادات الأمان في Streamlit
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("يرجى التأكد من إضافة مفتاح GEMINI_API_KEY في إعدادات Secrets.")
    st.stop()

# 3. إعداد نموذج الذكاء الاصطناعي مع "التلقين" الصارم
system_instruction = """
أنت مساعد تعليمي ذكي للطلاب. لقد قام الطالب برفع كتاب مدرسي بصيغة PDF.
مهمتك هي الإجابة على أسئلة الطالب بناءً على محتوى هذا الكتاب فقط. 
عند تقديم الإجابة، يجب أن تكتب في نهايتها رقم الصفحة (أو الصفحات) التي استخرجت منها المعلومات بوضوح.
إذا سألك الطالب سؤالاً وإجابته غير موجودة في هذا الكتاب المرفق، يُمنع منعاً باتاً أن تؤلف إجابة من خارج الكتاب. 
في هذه الحالة، يجب أن ترد بالنص التالي حرفياً: "عذراً، الإجابة على هذا السؤال غير متوفرة في الكتاب المدرسي الحالي. أنصحك بالبحث باستخدام أدوات الذكاء الاصطناعي العامة مثل ChatGPT أو Gemini للحصول على مساعدة إضافية."
عليك التحدث باللغة العربية الفصحى دائماً وبأسلوب ودود ومبسط للطالب.
"""

# تهيئة النموذج
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction
)

# 4. تهيئة ذاكرة المحادثة في Streamlit
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. واجهة رفع الملف (الكتاب المدرسي)
uploaded_file = st.file_uploader("قم بتحميل الكتاب المدرسي بصيغة PDF", type=["pdf"])

if uploaded_file and st.session_state.chat_session is None:
    with st.spinner("جاري قراءة الكتاب واستيعاب المنهج... يرجى الانتظار ⏳"):
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
                    {"role": "user", "parts": [gemini_file, "هذا هو الكتاب المدرسي. يرجى قراءته والاعتماد عليه فقط للإجابة على أسئلتي القادمة بناءً على التعليمات المعطاة لك."]}
                ]
            )
            st.success("✅ تم قراءة الكتاب بنجاح! يمكنك الآن طرح أسئلتك بالأسفل.")
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة الملف: {e}")
        finally:
            # حذف الملف المؤقت من الخادم
            os.remove(tmp_path)

# 6. عرض سجل المحادثة
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 7. واجهة الدردشة (لا تظهر إلا بعد رفع الكتاب)
if st.session_state.chat_session is not None:
    user_prompt = st.chat_input("اسألني عن أي شيء في المنهج...")
    
    if user_prompt:
        # عرض رسالة المستخدم
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        # الحصول على الرد من البوت
        with st.chat_message("assistant"):
            with st.spinner("جاري البحث في الكتاب..."):
                response = st.session_state.chat_session.send_message(user_prompt)
                st.markdown(response.text)
        
        # حفظ رد البوت في السجل
        st.session_state.messages.append({"role": "assistant", "content": response.text})