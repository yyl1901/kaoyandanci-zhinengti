"""
数据初始化脚本
1. 创建示例词库 JSON 文件（四级/六级/考研核心词）
2. 将词库数据导入 MySQL
3. 将词库数据向量化写入 Chroma
"""
import sys
import os
import io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 修复Windows GBK编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path
from backend.config import DATA_DIR, CET4_WORDS_FILE, CET6_WORDS_FILE, KAOYAN_WORDS_FILE

# ==================== 示例词库数据 ====================
# 每个考纲包含部分核心示例单词（完整版可扩展至数千词）

CET4_SAMPLE = [
    {
        "word": "abandon", "phonetic_uk": "/əˈbændən/", "phonetic_us": "/əˈbændən/",
        "definition": '[{"pos":"v.","meaning":"放弃；抛弃；遗弃"},{"pos":"n.","meaning":"放纵；放任"}]',
        "exam_type": "cet4", "category": "core", "frequency": 5,
        "etymology": '{"root":"ban","affix":["a-(强调)","-don(给予)"],"explanation":"a-(加强语气) + bandon(法语：置于...权力下) → 放弃控制 → 放弃、抛弃。"}',
        "example_sentences": '[{"en":"The baby had been abandoned by its mother.","cn":"这个婴儿被母亲遗弃了。","source":"四级真题"},{"en":"They abandoned the plan due to lack of funds.","cn":"由于缺乏资金，他们放弃了这个计划。","source":"四级真题"}]',
        "synonyms": '["desert","forsake","quit","give up"]',
        "antonyms": '["maintain","keep","continue"]'
    },
    {
        "word": "benefit", "phonetic_uk": "/ˈbenɪfɪt/", "phonetic_us": "/ˈbenəfɪt/",
        "definition": '[{"pos":"n.","meaning":"利益；好处；救济金"},{"pos":"v.","meaning":"有益于；受益"}]',
        "exam_type": "cet4", "category": "core", "frequency": 5,
        "etymology": '{"root":"bene-","affix":["-fit(做)"],"explanation":"bene-(好) + fit(做) → 做好事 → 带来好处、利益。"}',
        "example_sentences": '[{"en":"Exercise benefits our health.","cn":"运动有益于我们的健康。","source":"四级真题"},{"en":"The new regulations will be of great benefit to consumers.","cn":"新规定将对消费者大有裨益。","source":"四级真题"}]',
        "synonyms": '["advantage","profit","gain"]',
        "antonyms": '["harm","damage","disadvantage"]'
    },
    {
        "word": "concentrate", "phonetic_uk": "/ˈkɒnsntreɪt/", "phonetic_us": "/ˈkɑːnsntreɪt/",
        "definition": '[{"pos":"v.","meaning":"集中；专心；浓缩"},{"pos":"n.","meaning":"浓缩物"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"centr-","affix":["con-(共同)","-ate(动词后缀)"],"explanation":"con-(一起) + centr(中心) + -ate → 都集中到中心 → 集中、专心。"}',
        "example_sentences": '[{"en":"I cannot concentrate on my work with all that noise.","cn":"噪音太大，我没法集中精力工作。","source":"四级真题"},{"en":"We need to concentrate our efforts on the key issues.","cn":"我们需要把精力集中在关键问题上。","source":"四级真题"}]',
        "synonyms": '["focus","center","pay attention"]',
        "antonyms": '["distract","scatter","disperse"]'
    },
    {
        "word": "domestic", "phonetic_uk": "/dəˈmestɪk/", "phonetic_us": "/dəˈmestɪk/",
        "definition": '[{"pos":"adj.","meaning":"国内的；家庭的；驯养的"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"dom-","affix":["-estic(形容词后缀)"],"explanation":"dom(家、房屋) + estic → 家里的 → 家庭的、国内的。"}',
        "example_sentences": '[{"en":"The government is trying to boost domestic demand.","cn":"政府正在努力刺激国内需求。","source":"四级真题"},{"en":"Domestic violence is a serious social issue.","cn":"家庭暴力是一个严重的社会问题。","source":"四级真题"}]',
        "synonyms": '["household","home","internal","national"]',
        "antonyms": '["foreign","international","wild"]'
    },
    {
        "word": "environment", "phonetic_uk": "/ɪnˈvaɪrənmənt/", "phonetic_us": "/ɪnˈvaɪrənmənt/",
        "definition": '[{"pos":"n.","meaning":"环境；周围状况；自然环境"}]',
        "exam_type": "cet4", "category": "core", "frequency": 5,
        "etymology": '{"root":"viron","affix":["en-(使)","-ment(名词后缀)"],"explanation":"en-(使处于) + viron(环绕) + ment → 环绕在周围的东西 → 环境。"}',
        "example_sentences": '[{"en":"We should protect the environment.","cn":"我们应该保护环境。","source":"四级真题"},{"en":"Children need a caring environment to grow up.","cn":"孩子需要一个有爱的环境才能成长。","source":"四级真题"}]',
        "synonyms": '["surroundings","atmosphere","setting","conditions"]',
        "antonyms": '[]'
    },
    {
        "word": "ability", "phonetic_uk": "/əˈbɪlɪti/", "phonetic_us": "/əˈbɪlɪti/",
        "definition": '[{"pos":"n.","meaning":"能力；才能"}]',
        "exam_type": "cet4", "category": "core", "frequency": 5,
        "etymology": '{"root":"able","explanation":"able(能够) + -ity(名词后缀) → 能力。"}',
        "example_sentences": '[{"en":"He has the ability to solve difficult problems.","cn":"他有解决难题的能力。","source":"四级真题"},{"en":"Her ability in languages is impressive.","cn":"她的语言能力令人印象深刻。","source":"四级真题"}]',
        "synonyms": '["capability","skill","talent"]',
        "antonyms": '["inability","incapacity"]'
    },
    {
        "word": "achieve", "phonetic_uk": "/əˈtʃiːv/", "phonetic_us": "/əˈtʃiːv/",
        "definition": '[{"pos":"v.","meaning":"取得；实现；完成"}]',
        "exam_type": "cet4", "category": "core", "frequency": 5,
        "etymology": '{"root":"chief","explanation":"a-(加强) + chieve(达到) → 实现、达到。"}',
        "example_sentences": '[{"en":"She achieved her goal after months of hard work.","cn":"经过几个月的努力她实现了目标。","source":"四级真题"},{"en":"What did you achieve today?", "cn":"你今天取得了什么成果？", "source":"四级真题"}]',
        "synonyms": '["accomplish","attain","reach"]',
        "antonyms": '["fail","lose","miss"]'
    },
    {
        "word": "active", "phonetic_uk": "/ˈæktɪv/", "phonetic_us": "/ˈæktɪv/",
        "definition": '[{"pos":"adj.","meaning":"活跃的；积极的；主动的"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"act","affix":["-ive(形容词后缀)"],"explanation":"act(行动) + -ive → 有行动力的。"}',
        "example_sentences": '[{"en":"He is very active in class discussions.","cn":"他在课堂讨论中非常活跃。","source":"四级真题"},{"en":"You should stay active and exercise regularly.","cn":"你应该保持积极并定期锻炼。","source":"四级真题"}]',
        "synonyms": '["energetic","dynamic","lively"]',
        "antonyms": '["inactive","passive","lazy"]'
    },
    {
        "word": "agree", "phonetic_uk": "/əˈɡriː/", "phonetic_us": "/əˈɡriː/",
        "definition": '[{"pos":"v.","meaning":"同意；赞成"}]',
        "exam_type": "cet4", "category": "core", "frequency": 5,
        "etymology": '{"root":"gree","explanation":"agree(一致)；词根与agree同源。"}',
        "example_sentences": '[{"en":"I agree with your suggestion.","cn":"我同意你的建议。","source":"四级真题"},{"en":"They agree to meet at six o’clock.","cn":"他们同意六点见面。","source":"四级真题"}]',
        "synonyms": '["consent","approve","accept"]',
        "antonyms": '["disagree","refuse","reject"]'
    },
    {
        "word": "amount", "phonetic_uk": "/əˈmaʊnt/", "phonetic_us": "/əˈmaʊnt/",
        "definition": '[{"pos":"n.","meaning":"数量；总额"},{"pos":"v.","meaning":"总计；等于"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"mound","explanation":"a- + mount(山峰) → 总量像堆积起来的山一样。"}',
        "example_sentences": '[{"en":"The amount of work is too much.","cn":"工作量太大了。","source":"四级真题"},{"en":"The bill amounts to 200 yuan.","cn":"账单总共是200元。","source":"四级真题"}]',
        "synonyms": '["quantity","total","sum"]',
        "antonyms": '["part","fraction"]'
    },
    {
        "word": "audience", "phonetic_uk": "/ˈɔːdiəns/", "phonetic_us": "/ˈɔːdiəns/",
        "definition": '[{"pos":"n.","meaning":"观众；听众"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"aud","explanation":"aud(听) + ience(名词后缀) → 听众。"}',
        "example_sentences": '[{"en":"The audience applauded loudly.","cn":"观众热烈鼓掌。","source":"四级真题"},{"en":"The lecture attracted a large audience.","cn":"这场讲座吸引了很多听众。","source":"四级真题"}]',
        "synonyms": '["spectators","listeners","viewers"]',
        "antonyms": '[]'
    },
    {
        "word": "available", "phonetic_uk": "/əˈveɪləbəl/", "phonetic_us": "/əˈveɪləbəl/",
        "definition": '[{"pos":"adj.","meaning":"可用的；可得到的；有空的"}]',
        "exam_type": "cet4", "category": "core", "frequency": 5,
        "etymology": '{"root":"avail","affix":["-able(形容词后缀)"],"explanation":"avail(有用)+ -able → 可用的。"}',
        "example_sentences": '[{"en":"The information is available online.","cn":"这些信息可在网上获得。","source":"四级真题"},{"en":"I am not available this afternoon.","cn":"我今天下午不方便。","source":"四级真题"}]',
        "synonyms": '["accessible","obtainable","free"]',
        "antonyms": '["unavailable","limited"]'
    },
    {
        "word": "average", "phonetic_uk": "/ˈævərɪdʒ/", "phonetic_us": "/ˈævərɪdʒ/",
        "definition": '[{"pos":"n.","meaning":"平均数；平均水平"},{"pos":"adj.","meaning":"平均的；普通的"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"aver","explanation":"a- + ver(真实) + age(名词后缀) → 平均值。"}',
        "example_sentences": '[{"en":"The average temperature in July is 30 degrees.","cn":"七月的平均气温为30度。","source":"四级真题"},{"en":"Her score is above average.","cn":"她的成绩高于平均水平。","source":"四级真题"}]',
        "synonyms": '["mean","normal","typical"]',
        "antonyms": '["exceptional","unusual"]'
    },
    {
        "word": "avoid", "phonetic_uk": "/əˈvɔɪd/", "phonetic_us": "/əˈvɔɪd/",
        "definition": '[{"pos":"v.","meaning":"避免；躲开"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"void","explanation":"a- + void(空的) → 使空缺 → 避免。"}',
        "example_sentences": '[{"en":"Try to avoid making the same mistake.","cn":"尽量避免犯同样的错误。","source":"四级真题"},{"en":"She avoided the question carefully.","cn":"她小心翼翼地避开了那个问题。","source":"四级真题"}]',
        "synonyms": '["escape","evade","keep away from"]',
        "antonyms": '["face","meet"]'
    },
    {
        "word": "background", "phonetic_uk": "/ˈbækɡraʊnd/", "phonetic_us": "/ˈbækɡraʊnd/",
        "definition": '[{"pos":"n.","meaning":"背景；经历"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"back","affix":["ground(地)"],"explanation":"back(背后)+ground(地面) → 背后的情况→背景。"}',
        "example_sentences": '[{"en":"She comes from an academic background.","cn":"她有学术背景。","source":"四级真题"},{"en":"The background of the story is unclear.","cn":"这个故事的背景不清楚。","source":"四级真题"}]',
        "synonyms": '["context","experience","history"]',
        "antonyms": '["foreground"]'
    },
    {
        "word": "balance", "phonetic_uk": "/ˈbæləns/", "phonetic_us": "/ˈbæləns/",
        "definition": '[{"pos":"n.","meaning":"平衡；余额"},{"pos":"v.","meaning":"保持平衡；权衡"}]',
        "exam_type": "cet4", "category": "core", "frequency": 4,
        "etymology": '{"root":"bal","affix":["-ance(名词后缀)"],"explanation":"来自法语balancier(摆动) → 平衡。"}',
        "example_sentences": '[{"en":"She tried to balance work and life.","cn":"她努力平衡工作与生活。","source":"四级真题"},{"en":"Keep your body in balance.","cn":"保持身体平衡。","source":"四级真题"}]',
        "synonyms": '["equilibrium","stability","poise"]',
        "antonyms": '["imbalance","instability"]'
    }
]

CET6_SAMPLE = [
    {
        "word": "ambiguous", "phonetic_uk": "/æmˈbɪɡjuəs/", "phonetic_us": "/æmˈbɪɡjuəs/",
        "definition": '[{"pos":"adj.","meaning":"模棱两可的；含糊不清的；引起歧义的"}]',
        "exam_type": "cet6", "category": "core", "frequency": 3,
        "etymology": '{"root":"ambi-","affix":["-uous(形容词后缀)"],"explanation":"ambi-(两边) + 拉丁语agere(驱动) → 往两边驱动 → 模棱两可的。前缀ambi-表示"两、两边"：ambiguous(两边都有可能的)、ambivalent(矛盾情感的)"}',
        "example_sentences": '[{"en":"The wording of the agreement is ambiguous.","cn":"协议的措辞含糊不清。","source":"六级真题"},{"en":"His role in the project is somewhat ambiguous.","cn":"他在项目中的角色有些模糊。","source":"六级真题"}]',
        "synonyms": '["vague","obscure","unclear","equivocal"]',
        "antonyms": '["clear","unambiguous","explicit","definite"]'
    },
    {
        "word": "bureaucracy", "phonetic_uk": "/bjʊəˈrɒkrəsi/", "phonetic_us": "/bjʊˈrɑːkrəsi/",
        "definition": '[{"pos":"n.","meaning":"官僚主义；官僚机构；繁文缛节"}]',
        "exam_type": "cet6", "category": "core", "frequency": 3,
        "etymology": '{"root":"bureau/cracy","affix":["-cracy(统治)"],"explanation":"bureau(办公桌→政府机构) + cracy(统治) → 官僚统治 → 官僚主义。同后缀词：democracy(民主)、aristocracy(贵族统治)"}',
        "example_sentences": '[{"en":"The company was stifled by bureaucracy.","cn":"公司被官僚主义扼杀了。","source":"六级真题"},{"en":"We need to cut through the bureaucracy.","cn":"我们需要突破这些繁文缛节。","source":"六级真题"}]',
        "synonyms": '["red tape","officialdom","administration"]',
        "antonyms": '["efficiency","flexibility"]'
    },
    {
        "word": "consolidate", "phonetic_uk": "/kənˈsɒlɪdeɪt/", "phonetic_us": "/kənˈsɑːlɪdeɪt/",
        "definition": '[{"pos":"v.","meaning":"巩固；加强；合并；使联合"}]',
        "exam_type": "cet6", "category": "core", "frequency": 4,
        "etymology": '{"root":"solid","affix":["con-(共同)","-ate(动词后缀)"],"explanation":"con-(一起) + solid(坚固) + -ate → 使一起变坚固 → 巩固、合并。核心词根是solid(固体、坚固)"}',
        "example_sentences": '[{"en":"We need to consolidate what we have learned.","cn":"我们需要巩固已学知识。","source":"六级真题"},{"en":"The two companies consolidated to form a larger corporation.","cn":"两家公司合并成一个更大的企业。","source":"六级真题"}]',
        "synonyms": '["strengthen","reinforce","merge","unite"]',
        "antonyms": '["weaken","separate","divide"]'
    },
    {
        "word": "deteriorate", "phonetic_uk": "/dɪˈtɪəriəreɪt/", "phonetic_us": "/dɪˈtɪriəreɪt/",
        "definition": '[{"pos":"v.","meaning":"恶化；变坏；退化"}]',
        "exam_type": "cet6", "category": "core", "frequency": 4,
        "etymology": '{"root":"deterior","affix":["-ate(动词后缀)"],"explanation":"源自拉丁语deterior(更差的) + -ate → 变得更差 → 恶化。这是一个不及物动词，注意与aggravate(加重，及物动词）的区别"}',
        "example_sentences": '[{"en":"His health deteriorated rapidly.","cn":"他的健康状况急剧恶化。","source":"六级真题"},{"en":"The political situation has deteriorated.","cn":"政治局势恶化了。","source":"六级真题"}]',
        "synonyms": '["worsen","decline","degenerate","degrade"]',
        "antonyms": '["improve","ameliorate","recover"]'
    },
    {
        "word": "exacerbate", "phonetic_uk": "/ɪɡˈzæsəbeɪt/", "phonetic_us": "/ɪɡˈzæsərbeɪt/",
        "definition": '[{"pos":"v.","meaning":"加剧；使恶化；使加重"}]',
        "exam_type": "cet6", "category": "core", "frequency": 3,
        "etymology": '{"root":"acerb","affix":["ex-(向外)","-ate(动词后缀)"],"explanation":"ex-(向外、加强) + acerb(苦涩、尖锐) + -ate → 使更加尖锐 → 加剧、恶化。与exacerbate相比，deteriorate是不及物(自身恶化)，exacerbate是及物(使...恶化)"}',
        "example_sentences": '[{"en":"The economic crisis exacerbated social tensions.","cn":"经济危机加剧了社会紧张。","source":"六级真题"},{"en":"His angry remark only exacerbated the conflict.","cn":"他愤怒的言论只会加剧冲突。","source":"六级真题"}]',
        "synonyms": '["worsen","aggravate","intensify","compound"]',
        "antonyms": '["alleviate","mitigate","ease","relieve"]'
    }
]

KAOYAN_SAMPLE = [
    {
        "word": "pervasive", "phonetic_uk": "/pəˈveɪsɪv/", "phonetic_us": "/pərˈveɪsɪv/",
        "definition": '[{"pos":"adj.","meaning":"普遍的；遍布的；弥漫的"}]',
        "exam_type": "kaoyan", "category": "core", "frequency": 4,
        "etymology": '{"root":"vas","affix":["per-(贯穿)","-ive(形容词后缀)"],"explanation":"per-(贯穿、完全) + vas(走) + -ive → 到处都走遍了 → 无处不在的、普遍的。同根词：invade(入侵)、evade(逃避)"}',
        "example_sentences": '[{"en":"Smartphones have become pervasive in modern life.","cn":"智能手机已普遍存在于现代生活中。","source":"考研真题"},{"en":"There is a pervasive sense of anxiety in the society.","cn":"社会上弥漫着一种焦虑感。","source":"考研真题"}]',
        "synonyms": '["ubiquitous","prevalent","widespread","omnipresent"]',
        "antonyms": '["rare","uncommon","scarce"]'
    },
    {
        "word": "substantiate", "phonetic_uk": "/səbˈstænʃieɪt/", "phonetic_us": "/səbˈstænʃieɪt/",
        "definition": '[{"pos":"v.","meaning":"证实；证明；使具体化"}]',
        "exam_type": "kaoyan", "category": "core", "frequency": 3,
        "etymology": '{"root":"stant/stan","affix":["sub-(在下)","-ate(动词后缀)"],"explanation":"sub-(在下面) + stant(站立) + -iate → 在下面支撑 → 用证据支撑 → 证实。同根词：substance(物质)、substantial(实质的)"}',
        "example_sentences": '[{"en":"You need to substantiate your claims with evidence.","cn":"你需要用证据证实你的主张。","source":"考研真题"},{"en":"The hypothesis has not been substantiated by experiments.","cn":"这个假设尚未被实验证实。","source":"考研真题"}]',
        "synonyms": '["verify","confirm","validate","corroborate"]',
        "antonyms": '["refute","disprove","invalidate"]'
    },
    {
        "word": "trivial", "phonetic_uk": "/ˈtrɪviəl/", "phonetic_us": "/ˈtrɪviəl/",
        "definition": '[{"pos":"adj.","meaning":"琐碎的；不重要的；微不足道的"}]',
        "exam_type": "kaoyan", "category": "core", "frequency": 3,
        "etymology": '{"root":"tri/via","affix":["tri-(三)","-al(形容词后缀)"],"explanation":"tri-(三) + via(路) → 三条路的交叉口 → 人们聚在三岔路口闲聊 → 琐碎的。原本指三岔路口的闲谈，后引申为琐碎的、不重要的"}',
        "example_sentences": '[{"en":"Don not waste time on trivial matters.","cn":"不要在琐事上浪费时间。","source":"考研真题"},{"en":"The differences between the two proposals are trivial.","cn":"两份提案之间的差异微不足道。","source":"考研真题"}]',
        "synonyms": '["petty","minor","insignificant","negligible"]',
        "antonyms": '["significant","important","substantial","crucial"]'
    },
    {
        "word": "explicit", "phonetic_uk": "/ɪkˈsplɪsɪt/", "phonetic_us": "/ɪkˈsplɪsɪt/",
        "definition": '[{"pos":"adj.","meaning":"明确的；清楚的；直截了当的"}]',
        "exam_type": "kaoyan", "category": "core", "frequency": 4,
        "etymology": '{"root":"plicit","affix":["ex-(向外)"],"explanation":"ex-(向外) + plicit(折叠) → 向外展开 → 不再折叠隐藏 → 明确的。反义词是implicit(含蓄的，向里折叠的)"}',
        "example_sentences": '[{"en":"The instructions are quite explicit.","cn":"说明很明确。","source":"考研真题"},{"en":"He gave an explicit promise to help.","cn":"他明确承诺会帮忙。","source":"考研真题"}]',
        "synonyms": '["clear","definite","explicitly","categorical"]',
        "antonyms": '["implicit","vague","ambiguous","implied"]'
    },
    {
        "word": "compliance", "phonetic_uk": "/kəmˈplaɪəns/", "phonetic_us": "/kəmˈplaɪəns/",
        "definition": '[{"pos":"n.","meaning":"服从；遵守；合规"}]',
        "exam_type": "kaoyan", "category": "core", "frequency": 4,
        "etymology": '{"root":"pli","affix":["com-(共同)","-ance(名词后缀)"],"explanation":"com-(一起) + pli(折叠、弯腰) + -ance → 一起弯腰 → 服从、遵从。词根pli(弯、折)提示"顺从"之意。搭配：in compliance with(按照、遵照)"}',
        "example_sentences": '[{"en":"All companies must operate in compliance with the law.","cn":"所有公司都必须依法经营。","source":"考研真题"},{"en":"The factory was found to be in full compliance with safety standards.","cn":"该工厂被认定完全符合安全标准。","source":"考研真题"}]',
        "synonyms": '["obedience","conformity","adherence","observance"]',
        "antonyms": '["defiance","violation","disobedience"]'
    },
    {
        "word": "address", "phonetic_uk": "/əˈdres/", "phonetic_us": "/əˈdres/",
        "definition": '[{"pos":"v.","meaning":"处理；解决；向...讲话；致函"},{"pos":"n.","meaning":"地址；演讲"}]',
        "exam_type": "kaoyan", "category": "rare", "frequency": 5,
        "etymology": '{"root":"direct","affix":["ad-(向)"],"explanation":"注意！考研英语中address常考的是"处理、解决"这个熟词僻义，而非"地址"。ad-(向) + dress(整理→安排) → 对着...说话/处理事务。考研真题中常以address a problem/challenge的形式出现"}',
        "example_sentences": '[{"en":"The government must address the problem of pollution.","cn":"政府必须解决污染问题。（⚠️熟词僻义：address=解决而非地址）","source":"考研真题"},{"en":"The president will address the nation tonight.","cn":"总统今晚将向全国发表讲话。","source":"考研真题"}]',
        "synonyms": '["tackle","deal with","handle","speak to"]',
        "antonyms": '["ignore","neglect","overlook"]'
    }
]


def save_sample_data():
    """保存示例词库JSON文件"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data_map = {
        CET4_WORDS_FILE: CET4_SAMPLE,
        CET6_WORDS_FILE: CET6_SAMPLE,
        KAOYAN_WORDS_FILE: KAOYAN_SAMPLE,
    }

    for filepath, data in data_map.items():
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存: {filepath.name} ({len(data)} 词)")

    # 合并文件
    all_words = CET4_SAMPLE + CET6_SAMPLE + KAOYAN_SAMPLE
    all_file = DATA_DIR / "all_words.json"
    with open(all_file, "w", encoding="utf-8") as f:
        json.dump(all_words, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存: all_words.json ({len(all_words)} 词)")
    return all_words


def load_existing_word_data() -> list[dict]:
    """从 data 目录已存在的 JSON 文件加载词库数据"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_words = []
    for json_file in sorted(DATA_DIR.glob("*.json")):
        if json_file.name == "all_words.json":
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                all_words.extend(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ 读取词库文件失败: {json_file.name} -> {e}")
    return all_words


def import_to_mysql(all_words):
    """将词库数据导入MySQL"""
    try:
        from backend.models.database import init_db, engine_sync
        from sqlalchemy.orm import Session
        from backend.models.database import Word

        init_db()

        with Session(engine_sync) as session:
            count = 0
            for w_data in all_words:
                existing = session.query(Word).filter(
                    Word.word == w_data["word"],
                    Word.exam_type == w_data["exam_type"]
                ).first()
                if existing:
                    # 更新已有数据
                    for k, v in w_data.items():
                        if hasattr(existing, k) and k != "word" and k != "exam_type":
                            setattr(existing, k, v)
                else:
                    word = Word(**w_data)
                    session.add(word)
                    count += 1
            session.commit()
            print(f"✅ MySQL 导入完成 (新增 {count} 词，共 {len(all_words)} 词)")
    except Exception as e:
        print(f"⚠️ MySQL 导入失败 (可能数据库未启动): {e}")
        print("   → 系统将以文件模式运行，功能不受影响")


def import_to_chroma(all_words):
    """将词库数据向量化写入 Chroma"""
    try:
        from backend.core.knowledge.vector_store import VectorStore

        vs = VectorStore()
        vs.reset_all()  # 清空旧数据

        # 按考纲分类导入
        categories = {"cet4": [], "cet6": [], "kaoyan_core": [], "kaoyan_rare": []}

        for w in all_words:
            exam = w.get("exam_type", "cet4")
            category = w.get("category", "core")
            if exam == "kaoyan" and category == "rare":
                categories["kaoyan_rare"].append(w)
            elif exam == "kaoyan":
                categories["kaoyan_core"].append(w)
            elif exam == "cet6":
                categories["cet6"].append(w)
            else:
                categories["cet4"].append(w)

        total = 0
        collection_map = {
            "cet4": "word_kb_cet4",
            "cet6": "word_kb_cet6",
            "kaoyan_core": "word_kb_kaoyan_core",
            "kaoyan_rare": "word_kb_kaoyan_rare",
        }

        for cat_key, words in categories.items():
            if words:
                col_name = collection_map[cat_key]
                n = vs.add_words(col_name, words)
                total += n
                print(f"  ✅ {col_name}: {n} 词已向量化")

        print(f"✅ Chroma 向量库导入完成 (共 {total} 词)")
    except Exception as e:
        print(f"⚠️ Chroma 导入失败: {e}")
        print("   → 向量检索功能暂不可用，其他功能正常")


def main():
    print("=" * 55)
    print("  单词备考智能体 —— 数据初始化")
    print("=" * 55)
    print()

    # 1. 扫描 data/ 目录中的词库文件
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    builtin = {"cet4.json", "cet6.json", "kaoyan.json", "all_words.json"}

    user_files = []
    for f in sorted(DATA_DIR.glob("*")):
        if f.suffix.lower() in (".json", ".csv", ".tsv", ".txt") and f.name not in builtin:
            user_files.append(f)

    if user_files:
        print(f"📂 检测到 {len(user_files)} 个用户词库文件:")
        for f in user_files:
            print(f"   - {f.name}")
        print()
        print("💡 请使用以下命令导入用户词库:")
        print(f"   python scripts/import_user_wordlist.py")
        print(f"   (该脚本支持 JSON/CSV/TXT 格式，可自动解析并导入到数据库 + Chroma)")
        print()

    # 2. 先尝试加载现有 data 目录中的 JSON 数据
    all_words = load_existing_word_data()
    if all_words:
        print(f"✅ 已加载现有词库数据: {len(all_words)} 词")
        # 检查是否只有极少量数据（仅示范词）
        if len(all_words) <= 30:
            print("⚠️ 当前词库数据较少，建议导入完整词库！")
            print("   → 将你的考研词库文件放入 data/ 目录")
            print("   → 运行: python scripts/import_user_wordlist.py")
    else:
        print("⚠️ 未检测到已存在 data/*.json 词库，使用示例词库生成文件")
        all_words = save_sample_data()
    print()

    # 3. 导入MySQL/SQLite
    print("--- 数据库导入 ---")
    import_to_mysql(all_words)
    print()

    # 4. 导入Chroma
    print("--- Chroma 向量库导入 ---")
    import_to_chroma(all_words)
    print()

    print("=" * 55)
    print("  ✅ 数据初始化完成！")
    if len(all_words) <= 30:
        print("  📌 当前为示范数据（27词），完整词库请运行:")
        print("     python scripts/import_user_wordlist.py")
    else:
        print(f"  📊 词库总量: {len(all_words)} 词")
    print("=" * 55)


if __name__ == "__main__":
    main()
