"""
O'zbekiston viloyatlari va tumanlarini bazaga yuklash.
Ishlatish: python -m scripts.seed_locations
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.location import Region, District

LOCATIONS = [
    {
        "name_uz": "Toshkent shahri", "name_ru": "город Ташкент",
        "slug": "tashkent-city", "order": 1,
        "districts": [
            {"name_uz": "Bektemir",       "name_ru": "Бектемир",       "slug": "bektemir"},
            {"name_uz": "Chilonzor",      "name_ru": "Чиланзар",       "slug": "chilonzor"},
            {"name_uz": "Mirzo Ulug'bek", "name_ru": "Мирзо-Улугбек", "slug": "mirzo-ulugbek"},
            {"name_uz": "Mirobod",        "name_ru": "Мирабад",        "slug": "mirobod"},
            {"name_uz": "Olmazor",        "name_ru": "Алмазар",        "slug": "olmazor"},
            {"name_uz": "Sergeli",        "name_ru": "Сергели",        "slug": "sergeli"},
            {"name_uz": "Shayxontohur",   "name_ru": "Шайхантахур",   "slug": "shayxontohur"},
            {"name_uz": "Uchtepa",        "name_ru": "Учтепа",         "slug": "uchtepa"},
            {"name_uz": "Yakkasaroy",     "name_ru": "Яккасарай",      "slug": "yakkasaroy"},
            {"name_uz": "Yunusobod",      "name_ru": "Юнусабад",       "slug": "yunusobod"},
            {"name_uz": "Yashnobod",      "name_ru": "Яшнабад",        "slug": "yashnobod"},
        ],
    },
    {
        "name_uz": "Toshkent viloyati", "name_ru": "Ташкентская область",
        "slug": "tashkent-region", "order": 2,
        "districts": [
            {"name_uz": "Angren",          "name_ru": "Ангрен",           "slug": "angren"},
            {"name_uz": "Bekobod",         "name_ru": "Бекабад",          "slug": "bekobod"},
            {"name_uz": "Bo'stonliq",      "name_ru": "Бостанлык",        "slug": "bostonliq"},
            {"name_uz": "Bo'ka",           "name_ru": "Бука",             "slug": "boka"},
            {"name_uz": "Chirchiq",        "name_ru": "Чирчик",           "slug": "chirchiq"},
            {"name_uz": "Ohangaron",       "name_ru": "Ахангаран",        "slug": "ohangaron"},
            {"name_uz": "Olmaliq",         "name_ru": "Алмалык",          "slug": "olmaliq"},
            {"name_uz": "Oqqo'rg'on",     "name_ru": "Аккурган",         "slug": "oqqorgon"},
            {"name_uz": "Parkent",         "name_ru": "Паркент",          "slug": "parkent"},
            {"name_uz": "Piskent",         "name_ru": "Пскент",           "slug": "piskent"},
            {"name_uz": "Qibray",          "name_ru": "Кибрай",           "slug": "qibray"},
            {"name_uz": "Toshkent tumani", "name_ru": "Ташкентский район","slug": "tashkent-tuman"},
            {"name_uz": "Urtachirchiq",    "name_ru": "Уртачирчик",       "slug": "urtachirchiq"},
            {"name_uz": "Yuqorichirchiq",  "name_ru": "Юкоричирчик",     "slug": "yuqorichirchiq"},
            {"name_uz": "Zangiota",        "name_ru": "Зангиота",         "slug": "zangiota"},
            {"name_uz": "Yangiyul",        "name_ru": "Янгиюль",          "slug": "yangiyul"},
        ],
    },
    {
        "name_uz": "Samarqand viloyati", "name_ru": "Самаркандская область",
        "slug": "samarqand", "order": 3,
        "districts": [
            {"name_uz": "Samarqand shahri","name_ru": "город Самарканд", "slug": "samarqand-city"},
            {"name_uz": "Bulung'ur",       "name_ru": "Булунгур",         "slug": "bulungur"},
            {"name_uz": "Ishtixon",        "name_ru": "Иштыхан",          "slug": "ishtixon"},
            {"name_uz": "Jomboy",          "name_ru": "Джамбай",          "slug": "jomboy"},
            {"name_uz": "Kattaqo'rg'on",  "name_ru": "Каттакурган",      "slug": "kattaqorgon"},
            {"name_uz": "Narpay",          "name_ru": "Нарпай",           "slug": "narpay"},
            {"name_uz": "Nurobod",         "name_ru": "Нурабад",          "slug": "nurobod"},
            {"name_uz": "Oqdaryo",         "name_ru": "Акдарья",          "slug": "oqdaryo"},
            {"name_uz": "Pastdarg'om",     "name_ru": "Пастдаргом",       "slug": "pastdargom"},
            {"name_uz": "Payariq",         "name_ru": "Пайарык",          "slug": "payariq"},
            {"name_uz": "Paxtachi",        "name_ru": "Пахтачи",          "slug": "paxtachi"},
            {"name_uz": "Qo'shrabot",      "name_ru": "Кушрабат",         "slug": "qoshrabot"},
            {"name_uz": "Toyloq",          "name_ru": "Тайлак",           "slug": "toyloq"},
            {"name_uz": "Urgut",           "name_ru": "Ургут",            "slug": "urgut"},
        ],
    },
    {
        "name_uz": "Farg'ona viloyati", "name_ru": "Ферганская область",
        "slug": "fergana", "order": 4,
        "districts": [
            {"name_uz": "Farg'ona shahri",    "name_ru": "город Фергана",    "slug": "fergana-city"},
            {"name_uz": "Qo'qon shahri",      "name_ru": "город Коканд",     "slug": "qoqon"},
            {"name_uz": "Marg'ilon shahri",   "name_ru": "город Маргилан",   "slug": "margilon"},
            {"name_uz": "Oltiariq",           "name_ru": "Алтыарык",         "slug": "oltiariq"},
            {"name_uz": "Bag'dod",            "name_ru": "Багдад",           "slug": "bagdod"},
            {"name_uz": "Beshariq",           "name_ru": "Бешарык",          "slug": "beshariq"},
            {"name_uz": "Buvayda",            "name_ru": "Бувайда",          "slug": "buvayda"},
            {"name_uz": "Dang'ara",           "name_ru": "Дангара",          "slug": "dangara"},
            {"name_uz": "Furqat",             "name_ru": "Фуркат",           "slug": "furqat"},
            {"name_uz": "Quva",               "name_ru": "Кува",             "slug": "quva"},
            {"name_uz": "Rishton",            "name_ru": "Риштан",           "slug": "rishton"},
            {"name_uz": "So'x",               "name_ru": "Сох",              "slug": "sox"},
            {"name_uz": "Toshloq",            "name_ru": "Ташлак",           "slug": "toshloq"},
            {"name_uz": "Uchko'prik",         "name_ru": "Учкуприк",         "slug": "uchkoprik"},
            {"name_uz": "O'zbekiston tumani", "name_ru": "Узбекистанский р-н","slug": "ozbekiston-tuman"},
            {"name_uz": "Yozyovon",           "name_ru": "Язъяван",          "slug": "yozyovon"},
        ],
    },
    {
        "name_uz": "Andijon viloyati", "name_ru": "Андижанская область",
        "slug": "andijan", "order": 5,
        "districts": [
            {"name_uz": "Andijon shahri", "name_ru": "город Андижан", "slug": "andijan-city"},
            {"name_uz": "Asaka",          "name_ru": "Асака",         "slug": "asaka"},
            {"name_uz": "Baliqchi",       "name_ru": "Балыкчи",       "slug": "baliqchi"},
            {"name_uz": "Bo'ston",        "name_ru": "Бустон",        "slug": "boston"},
            {"name_uz": "Buloqboshi",     "name_ru": "Булакбаши",     "slug": "buloqboshi"},
            {"name_uz": "Jalolquduq",     "name_ru": "Джалалкудук",   "slug": "jalolquduq"},
            {"name_uz": "Xo'jaobod",     "name_ru": "Ходжаабад",     "slug": "xojaobod"},
            {"name_uz": "Izboskan",       "name_ru": "Избаскан",      "slug": "izboskan"},
            {"name_uz": "Qo'rg'ontepa", "name_ru": "Кургантепа",    "slug": "qorgontepa"},
            {"name_uz": "Marhamat",       "name_ru": "Мархамат",      "slug": "marhamat"},
            {"name_uz": "Oltinko'l",     "name_ru": "Алтынкуль",     "slug": "oltinkol"},
            {"name_uz": "Paxtaobod",      "name_ru": "Пахтаабад",     "slug": "paxtaobod"},
            {"name_uz": "Shahrixon",      "name_ru": "Шахрихан",      "slug": "shahrixon"},
            {"name_uz": "Ulug'nor",      "name_ru": "Улугнор",       "slug": "ulugnor"},
        ],
    },
    {
        "name_uz": "Namangan viloyati", "name_ru": "Наманганская область",
        "slug": "namangan", "order": 6,
        "districts": [
            {"name_uz": "Namangan shahri", "name_ru": "город Наманган", "slug": "namangan-city"},
            {"name_uz": "Chortoq",         "name_ru": "Чартак",         "slug": "chortoq"},
            {"name_uz": "Chust",           "name_ru": "Чует",           "slug": "chust"},
            {"name_uz": "Kosonsoy",        "name_ru": "Касансай",       "slug": "kosonsoy"},
            {"name_uz": "Mingbuloq",       "name_ru": "Мингбулак",      "slug": "mingbuloq"},
            {"name_uz": "Norin",           "name_ru": "Нарын",          "slug": "norin"},
            {"name_uz": "Pop",             "name_ru": "Поп",            "slug": "pop"},
            {"name_uz": "To'raqo'rg'on", "name_ru": "Туракурган",     "slug": "toraqorgon"},
            {"name_uz": "Uychi",           "name_ru": "Уйчи",           "slug": "uychi"},
            {"name_uz": "Yangiqo'rg'on",  "name_ru": "Янгикурган",     "slug": "yangiqorgon"},
            {"name_uz": "Davlatobod",      "name_ru": "Давлатабад",     "slug": "davlatobod"},
        ],
    },
    {
        "name_uz": "Buxoro viloyati", "name_ru": "Бухарская область",
        "slug": "bukhara", "order": 7,
        "districts": [
            {"name_uz": "Buxoro shahri",  "name_ru": "город Бухара",   "slug": "bukhara-city"},
            {"name_uz": "G'ijduvon",     "name_ru": "Гиждуван",        "slug": "gijduvon"},
            {"name_uz": "Jondor",         "name_ru": "Жандор",          "slug": "jondor"},
            {"name_uz": "Kogon",          "name_ru": "Каган",           "slug": "kogon"},
            {"name_uz": "Olot",           "name_ru": "Алат",            "slug": "olot"},
            {"name_uz": "Peshku",         "name_ru": "Пешку",           "slug": "peshku"},
            {"name_uz": "Qorakul",        "name_ru": "Каракуль",        "slug": "qorakul"},
            {"name_uz": "Qorovulbozor",   "name_ru": "Каравулбазар",    "slug": "qarovulbozor"},
            {"name_uz": "Romitan",        "name_ru": "Ромитан",         "slug": "romitan"},
            {"name_uz": "Shofirkon",      "name_ru": "Шафиркан",        "slug": "shofirkon"},
            {"name_uz": "Vobkent",        "name_ru": "Вабкент",         "slug": "vobkent"},
        ],
    },
    {
        "name_uz": "Qashqadaryo viloyati", "name_ru": "Кашкадарьинская область",
        "slug": "kashkadarya", "order": 8,
        "districts": [
            {"name_uz": "Qarshi shahri",  "name_ru": "город Карши",    "slug": "qarshi-city"},
            {"name_uz": "Chiroqchi",      "name_ru": "Чиракчи",        "slug": "chiroqchi"},
            {"name_uz": "Dehqonobod",     "name_ru": "Дехканабад",     "slug": "dehqonobod"},
            {"name_uz": "G'uzor",        "name_ru": "Гузар",           "slug": "guzor"},
            {"name_uz": "Kasbi",          "name_ru": "Касби",           "slug": "kasbi"},
            {"name_uz": "Kitob",          "name_ru": "Китаб",           "slug": "kitob"},
            {"name_uz": "Koson",          "name_ru": "Косон",           "slug": "koson"},
            {"name_uz": "Mirishkor",      "name_ru": "Миришкор",        "slug": "mirishkor"},
            {"name_uz": "Muborak",        "name_ru": "Мубарек",         "slug": "muborak"},
            {"name_uz": "Nishon",         "name_ru": "Нишан",           "slug": "nishon"},
            {"name_uz": "Qamashi",        "name_ru": "Камаши",          "slug": "qamashi"},
            {"name_uz": "Shahrisabz",     "name_ru": "Шахрисабз",       "slug": "shahrisabz"},
            {"name_uz": "Yakkabog'",     "name_ru": "Яккабаг",         "slug": "yakkabog"},
            {"name_uz": "Baxmal",         "name_ru": "Бахмал",          "slug": "baxmal-qashqa"},
        ],
    },
    {
        "name_uz": "Surxondaryo viloyati", "name_ru": "Сурхандарьинская область",
        "slug": "surkhandarya", "order": 9,
        "districts": [
            {"name_uz": "Termiz shahri",  "name_ru": "город Термез",   "slug": "termiz-city"},
            {"name_uz": "Angor",          "name_ru": "Ангор",           "slug": "angor"},
            {"name_uz": "Bandixon",       "name_ru": "Бандихан",        "slug": "bandixon"},
            {"name_uz": "Boysun",         "name_ru": "Байсун",          "slug": "boysun"},
            {"name_uz": "Denov",          "name_ru": "Денау",           "slug": "denov"},
            {"name_uz": "Jarqo'rg'on",  "name_ru": "Джаркурган",      "slug": "jarqorgon"},
            {"name_uz": "Muzrabot",       "name_ru": "Музрабад",        "slug": "muzrabot"},
            {"name_uz": "Oltinsoy",       "name_ru": "Алтынсай",        "slug": "oltinsoy"},
            {"name_uz": "Qiziriq",        "name_ru": "Кизирик",         "slug": "qiziriq"},
            {"name_uz": "Sariosiyo",      "name_ru": "Сариасия",        "slug": "sariosiyo"},
            {"name_uz": "Sherobod",       "name_ru": "Шерабад",         "slug": "sherobod"},
            {"name_uz": "Shurchi",        "name_ru": "Шурчи",           "slug": "shurchi"},
            {"name_uz": "Uzun",           "name_ru": "Узун",            "slug": "uzun"},
            {"name_uz": "Xo'jaypok",     "name_ru": "Ходжайпак",       "slug": "xojaypok"},
        ],
    },
    {
        "name_uz": "Jizzax viloyati", "name_ru": "Джизакская область",
        "slug": "jizzakh", "order": 10,
        "districts": [
            {"name_uz": "Jizzax shahri",   "name_ru": "город Джизак",    "slug": "jizzakh-city"},
            {"name_uz": "Arnasoy",         "name_ru": "Арнасай",         "slug": "arnasoy"},
            {"name_uz": "Baxmal",          "name_ru": "Бахмал",          "slug": "baxmal-jizzax"},
            {"name_uz": "Do'stlik",       "name_ru": "Дустлик",         "slug": "dostlik"},
            {"name_uz": "Forish",          "name_ru": "Фариш",           "slug": "forish"},
            {"name_uz": "G'allaorol",     "name_ru": "Галляарал",       "slug": "gallaorol"},
            {"name_uz": "Mirzacho'l",     "name_ru": "Мирзачуль",       "slug": "mirzachol"},
            {"name_uz": "Paxtakor",        "name_ru": "Пахтакор",        "slug": "paxtakor"},
            {"name_uz": "Yangiobod",       "name_ru": "Янгиабад",        "slug": "yangiobod"},
            {"name_uz": "Zomin",           "name_ru": "Замин",           "slug": "zomin"},
            {"name_uz": "Zarbdor",         "name_ru": "Зарбдор",         "slug": "zarbdor"},
            {"name_uz": "Sharof Rashidov", "name_ru": "Шараф Рашидов",  "slug": "sharof-rashidov"},
        ],
    },
    {
        "name_uz": "Sirdaryo viloyati", "name_ru": "Сырдарьинская область",
        "slug": "sirdarya", "order": 11,
        "districts": [
            {"name_uz": "Guliston shahri", "name_ru": "город Гулистан", "slug": "guliston-city"},
            {"name_uz": "Boyovut",         "name_ru": "Баяут",          "slug": "boyovut"},
            {"name_uz": "Mirzaobod",       "name_ru": "Мирзаабад",      "slug": "mirzaobod"},
            {"name_uz": "Oqoltin",         "name_ru": "Акалтын",        "slug": "oqoltin"},
            {"name_uz": "Sardoba",         "name_ru": "Сардоба",        "slug": "sardoba"},
            {"name_uz": "Sayxunobod",      "name_ru": "Сайхунабад",     "slug": "sayxunobod"},
            {"name_uz": "Shirin",          "name_ru": "Ширин",          "slug": "shirin"},
            {"name_uz": "Xovos",           "name_ru": "Хавас",          "slug": "xovos"},
            {"name_uz": "Yangiyer",        "name_ru": "Янгиер",         "slug": "yangiyer"},
        ],
    },
    {
        "name_uz": "Navoiy viloyati", "name_ru": "Навоийская область",
        "slug": "navoi", "order": 12,
        "districts": [
            {"name_uz": "Navoiy shahri", "name_ru": "город Навои",  "slug": "navoi-city"},
            {"name_uz": "Karmana",       "name_ru": "Кармана",       "slug": "karmana"},
            {"name_uz": "Konimex",       "name_ru": "Конимех",       "slug": "konimex"},
            {"name_uz": "Navbahor",      "name_ru": "Навбахор",      "slug": "navbahor"},
            {"name_uz": "Nurota",        "name_ru": "Нурата",        "slug": "nurota"},
            {"name_uz": "Qiziltepa",     "name_ru": "Кизилтепа",    "slug": "qiziltepa"},
            {"name_uz": "Tomdi",         "name_ru": "Томди",         "slug": "tomdi"},
            {"name_uz": "Uchquduq",      "name_ru": "Учкудук",       "slug": "uchquduq"},
        ],
    },
    {
        "name_uz": "Xorazm viloyati", "name_ru": "Хорезмская область",
        "slug": "khorezm", "order": 13,
        "districts": [
            {"name_uz": "Urganch shahri", "name_ru": "город Ургенч",      "slug": "urganch-city"},
            {"name_uz": "Bog'ot",        "name_ru": "Богот",              "slug": "bogot"},
            {"name_uz": "Gurlan",         "name_ru": "Гурлен",             "slug": "gurlan"},
            {"name_uz": "Xiva",           "name_ru": "Хива",               "slug": "xiva"},
            {"name_uz": "Xazorasp",       "name_ru": "Хазарасп",           "slug": "xazorasp"},
            {"name_uz": "Qo'shko'pir",  "name_ru": "Кушкупыр",           "slug": "qoshkopir"},
            {"name_uz": "Shovot",         "name_ru": "Шават",              "slug": "shovot"},
            {"name_uz": "Tuproqqal'a",   "name_ru": "Тупроккала",         "slug": "tuproqqala"},
            {"name_uz": "Urganch tumani", "name_ru": "Ургенчский район",   "slug": "urganch-tuman"},
            {"name_uz": "Yangiariq",      "name_ru": "Янгиарык",           "slug": "yangiariq"},
            {"name_uz": "Yangibozor",     "name_ru": "Янгибазар",          "slug": "yangibozor"},
            {"name_uz": "Pitnak",         "name_ru": "Питнак",             "slug": "pitnak"},
        ],
    },
    {
        "name_uz": "Qoraqalpog'iston Respublikasi", "name_ru": "Республика Каракалпакстан",
        "slug": "karakalpakstan", "order": 14,
        "districts": [
            {"name_uz": "Nukus shahri",  "name_ru": "город Нукус",    "slug": "nukus-city"},
            {"name_uz": "Amudaryo",      "name_ru": "Амударья",        "slug": "amudaryo"},
            {"name_uz": "Beruniy",       "name_ru": "Беруний",         "slug": "beruniy"},
            {"name_uz": "Chimboy",       "name_ru": "Чимбай",          "slug": "chimboy"},
            {"name_uz": "Ellikkala",     "name_ru": "Элликкала",       "slug": "ellikkala"},
            {"name_uz": "Kegeyli",       "name_ru": "Кегейли",         "slug": "kegeyli"},
            {"name_uz": "Qo'ng'irot",  "name_ru": "Кунград",          "slug": "qongirot"},
            {"name_uz": "Muynoq",        "name_ru": "Муйнак",          "slug": "muynoq"},
            {"name_uz": "Nukus tumani",  "name_ru": "Нукусский район", "slug": "nukus-tuman"},
            {"name_uz": "Qanlikol",      "name_ru": "Канликуль",       "slug": "qanlikol"},
            {"name_uz": "Qorao'zak",    "name_ru": "Караузяк",        "slug": "qarаouzak"},
            {"name_uz": "Shumanay",      "name_ru": "Шуманай",         "slug": "shumanay"},
            {"name_uz": "Taxtako'pir",  "name_ru": "Тахтакупыр",      "slug": "taxtakopir"},
            {"name_uz": "To'rtko'l",   "name_ru": "Турткуль",         "slug": "tortkol"},
            {"name_uz": "Xo'jayli",    "name_ru": "Ходжейли",         "slug": "xojayli"},
        ],
    },
]


async def seed(db: AsyncSession) -> None:
    for region_data in LOCATIONS:
        region = Region(
            name_uz=region_data["name_uz"],
            name_ru=region_data["name_ru"],
            slug=region_data["slug"],
            order=region_data["order"],
        )
        db.add(region)
        await db.flush()

        for d in region_data["districts"]:
            db.add(District(
                region_id=region.id,
                name_uz=d["name_uz"],
                name_ru=d["name_ru"],
                slug=d["slug"],
            ))

    await db.commit()
    print(f"✓ {len(LOCATIONS)} viloyat va tumanlar yuklandi")


async def main():
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
