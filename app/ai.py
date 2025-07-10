from google import genai
from google.genai import types
from .models import Diseases

# pip install google-genai


def generate_prompt(image_path):
    kasalliklar=list(Diseases.objects.values_list("name",flat=True))
    # kasalliklar=[
    #     'Карам қурти', 'Тута абсолюта (Помидор куяси)', 'Оидиум', 'Ўргамчаккана', 'Намат канаси', ' Арча унсимон қурти',
    #     'Қалқондор', 'Олма мевахўри', 'Кузги тунлам (Илдиз қурти)', 'Бактериал куйиш', 'Бир йиллик икки паллали бегона ўтларга қарши',
    #     'Тупроқда озуқа етишмаяпти', 'Ғўза тунлами (Кўсак қурти) ', 'Стресс', 'Ажириқ ', 'Оқ бош', 'Бир йиллик бошоқли (тариқсимон бегона утлар)',
    #     'Ғилофли куя', 'Симқурт ', 'Колорадо қунғизи', 'Илдиз қурти', 'Ҳилол ', 'Барча бегона утларга', 'Монилиоз', 'Шиллиққурт', 'Антракноз',
    #     'Занг ', 'Пероноспороз', 'Барг бурмаси', 'Доғланиш ', 'Мильдю', 'Переноспориоз', 'Фитофтороз ', 'Фоммоз ', 'Ғалла пашаси', 'Пирикуляриоз',
    #     'Альтернариоз ', 'Макроспориоз ', 'Шингил баргўрари', 'Олма гулхўри', 'Визилдоқ қўнғиз ', 'Хасва ', 'Қандала  ', 'Маккажухори парвонаси',
    #     'Чигиртка ', 'Шарқ Мевахўри ', 'Комсток қурти', 'Оқ қанот', 'Ёввойи сули', 'Райграс', 'Ғумай ', 'Қамиш',
    #     'Клястероспориоз (Тешикчали доғланиш)', 'Курмак', 'Парша (калмараз)', 'Ун шудринг', 'Коккомикоз', 'Қорасон', 'Гоммоз ',
    #     'Септориоз', 'Замбуруғлик касалликлар', 'Озуқа етишмаслиги ', 'Шира ва трипс', 'Фузариоз', 'Зараркунандалар', 'Бегона ут',
    #     'Маккажухори парвонаси']
    client = genai.Client(
        api_key="AIzaSyCpXk8qWREU3N3o7VPwhhKgcp5cR9w6Gw0",
    )

    files = [
        # Please ensure that the file is available in local system working direrctory or change the file path.
        client.files.upload(file=image_path),
    ]

    model = "gemini-2.0-flash-lite"
    # model = "gemini-2.0-flash"
    # gemini-2.0-flash-preview-image-generation
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_uri(
                    file_uri=files[0].uri,
                    mime_type=files[0].mime_type,
                ),
                types.Part.from_text(
                    text=f"Suratdagi kasallikni bizdagi ro'yxatdan topib bering: {kasalliklar}.Va faqat eng yaqini nomini qaytar.")
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )
    result=""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        # print(chunk.text, end="")
        result+=chunk.text
    return result

# if __name__ == "__main__":
#     generate()
