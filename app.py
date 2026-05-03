import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# 1. إعداد الصفحة
st.set_page_config(page_title="المساعد التعليمي الذكي", page_icon="📚", layout="centered")
st.title("📚  3المساعد التعليمي الذكي")
st.markdown("مرحباً بك! ارفع كتابك المدرسي بصيغة PDF واسألني أي سؤال من المنهج.")

# 2. إعداد مفتاح API
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("يرجى التأكد من إضافة مفتاح GEMINI_API_KEY في إعدادات Secrets.")
    st.stop()

# 3. تهيئة النموذج الأساسي
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# 4. تهيئة المتغيرات في الذاكرة (تم إلغاء start_chat)
if "gemini_file" not in st.session_state:
    st.session_state.gemini_file = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. واجهة رفع الملف
uploaded_file = st.file_uploader("قم بتحميل الكتاب المدرسي بصيغة PDF", type=["pdf"])

if uploaded_file and st.session_state.gemini_file is None:
    with st.spinner("جاري قراءة الكتاب واستيعاب المنهج... قد يستغرق هذا بضع ثوانٍ ⏳"):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # رفع الملف إلى خوادم جوجل
            uploaded_gfile = genai.upload_file(path=tmp_path, display_name=uploaded_file.name)
            
            # الانتظار حتى تكتمل المعالجة
            while uploaded_gfile.state.name == "PROCESSING":
                time.sleep(3)
                uploaded_gfile = genai.get_file(uploaded_gfile.name)
            
            if uploaded_gfile.state.name == "FAILED":
                st.error("عذراً، حدث خطأ في خوادم جوجل أثناء معالجة هذا الكتاب.")
                st.stop()
            
            # حفظ الملف في ذاكرة التطبيق بدلاً من محاولة حشوه في جلسة محادثة
            st.session_state.gemini_file = uploaded_gfile
            st.success("✅ تم قراءة الكتاب بنجاح واستيعاب التعليمات! يمكنك الآن طرح أسئلتك بالأسفل.")
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة الملف: {e}")
        finally:
            os.remove(tmp_path)

# 6. عرض سجل المحادثة المرئي للطالب
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 7. واجهة الدردشة وبناء الذاكرة اليدوية (الحل السحري)
if st.session_state.gemini_file is not None:
    user_prompt = st.chat_input("اسألني عن أي شيء في المنهج...")
    
    if user_prompt:
        # 1. عرض وحفظ سؤال المستخدم
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        # 2. معالجة الإجابة
        with st.chat_message("assistant"):
            with st.spinner("جاري البحث في الكتاب..."):
                try:
                    # بناء تاريخ المحادثة يدوياً وإرساله دفعة واحدة للخادم
                    custom_history = []
                    
                    # أ. التلقين الصارم وإرفاق الكتاب (مخفي عن الطالب)
                    instruction = """
                    أنت مساعد تعليمي ذكي للطلاب. لقد قمت برفع كتاب مدرسي بصيغة PDF.
                    مهمتك هي الإجابة على أسئلة الطالب بناءً على محتوى هذا الكتاب فقط. 
                    عند تقديم الإجابة، يجب أن تكتب في نهايتها رقم الصفحة (أو الصفحات) التي استخرجت منها المعلومات بوضوح.
                    إذا كان السؤال لا توجد إجابته في الكتاب المرفق، يُمنع منعاً باتاً التأليف من خارج الكتاب. 
                    في هذه الحالة، يجب أن ترد حرفياً: "عذراً، الإجابة على هذا السؤال غير متوفرة في الكتاب المدرسي الحالي. أنصحك بالبحث باستخدام أدوات الذكاء الاصطناعي العامة مثل ChatGPT أو Gemini للحصول على مساعدة إضافية."
                    عليك التحدث باللغة العربية الفصحى.
                    """
                    custom_history.append({"role": "user", "parts": [st.session_state.gemini_file, instruction]})
                    custom_history.append({"role": "model", "parts": ["مفهوم. سألتزم بالكتاب المرفق فقط ولن أؤلف إجابات من خارجه، وسأذكر رقم الصفحة."]})
                    
                    # ب. إضافة المحادثات السابقة (لضمان تذكر البوت لسياق الكلام)
                    # نأخذ كل الرسائل السابقة ما عدا السؤال الأخير الذي أضفناه للتو
                    for msg in st.session_state.messages[:-1]:
                        # تحويل مسميات Streamlit إلى مسميات Gemini
                        role = "model" if msg["role"] == "assistant" else "user"
                        custom_history.append({"role": role, "parts": [msg["content"]]})
                        
                    # ج. إضافة السؤال الحالي
                    custom_history.append({"role": "user", "parts": [user_prompt]})
                    
                    # إرسال الحزمة بالكامل وتوليد الإجابة
                    response = model.generate_content(custom_history)
                    
                    # عرض الإجابة وحفظها
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالخادم: {e}")
