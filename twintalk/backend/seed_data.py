"""Seed script — populates the database with initial questionnaires.

Run: python seed_data.py
"""

import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_db
from models.questionnaire import Questionnaire, Question
from config import get_config


def seed_questionnaires(db):
    """Create the default questionnaire set."""

    # ========================================
    # 🌟 引导问卷 (Onboarding) — 第一次进入时完成
    # 基于用户建议的 8 个核心问题，快速建立初始画像
    # ========================================
    onboarding = Questionnaire(
        id=str(uuid.uuid4()),
        title="🌟 认识你自己",
        description="几个简单的问题，帮助你的数字分身快速了解你。大约需要 3 分钟。",
        category="onboarding",
        version=1,
        order_index=0,
    )
    db.add(onboarding)
    db.flush()

    onboarding_questions = [
        {
            "content": "你想让数字分身使用什么昵称来称呼你？",
            "type": "text",
            "dimension": "基本信息",
            "order": 1,
            "placeholder": "例如：小明、Lex、阿树……随你喜欢",
        },
        {
            "content": "你的年龄和性别是？",
            "type": "text",
            "dimension": "基本信息",
            "order": 2,
            "placeholder": "例如：25岁，女",
        },
        {
            "content": "你所在的城市是？",
            "type": "text",
            "dimension": "基本信息",
            "order": 3,
            "placeholder": "例如：北京、上海、广州……",
        },
        {
            "content": "你的职业或学生身份是什么？",
            "type": "text",
            "dimension": "基本信息",
            "order": 4,
            "placeholder": "例如：产品经理、大三学生、自由职业设计师……",
        },
        {
            "content": "你的 MBTI 是什么？用三个词形容你的性格。",
            "type": "text",
            "dimension": "性格",
            "order": 5,
            "placeholder": "例如：INFP，好奇、温柔、随性 / 不知道 MBTI，就直接写三个词",
        },
        {
            "content": "日常最常做、最感兴趣的三件事是什么？",
            "type": "text",
            "dimension": "兴趣爱好",
            "order": 6,
            "placeholder": "例如：刷剧、打羽毛球、研究咖啡豆",
        },
        {
            "content": "最近正在做的一件事是什么？",
            "type": "text",
            "dimension": "当下状态",
            "order": 7,
            "placeholder": "可以是工作项目、学习某样东西、准备某个计划……",
        },
        {
            "content": "近期有没有想做的事，或想接触的新领域？",
            "type": "text",
            "dimension": "当下状态",
            "order": 8,
            "placeholder": "例如：想学吉他、想了解 AI、想去某个地方旅行……没有也可以写没有",
        },
        {
            "content": "和人交流时，你更习惯哪种风格？",
            "type": "choice",
            "dimension": "沟通偏好",
            "order": 9,
            "choices": '["直白简洁，说到点子上", "温柔热情，照顾对方感受", "幽默随性，轻松自在", "视情况而定，灵活切换"]',
        },
        {
            "content": "有没有特别不想聊、或者让你不舒服的话题？",
            "type": "text",
            "dimension": "边界设定",
            "order": 10,
            "placeholder": "例如：政治、相亲、父母催婚……没有雷点也可以写「没有」",
        },
        {
            "content": "你的主要社交目的是什么？",
            "type": "choice",
            "dimension": "社交期望",
            "order": 11,
            "choices": '["寻找可能的的恋爱对象", "扩列认识相同兴趣的人", "找人倾听或树洞", "随缘佛系闲聊"]',
        },
    ]

    for q_data in onboarding_questions:
        q = Question(
            id=str(uuid.uuid4()),
            questionnaire_id=onboarding.id,
            content=q_data["content"],
            question_type=q_data["type"],
            dimension=q_data["dimension"],
            order_index=q_data["order"],
        )
        if q_data["type"] == "text":
            q.placeholder = q_data.get("placeholder", "")
        elif q_data["type"] in ("choice", "multi_choice"):
            q.choices = q_data.get("choices", "[]")
        db.add(q)

    # ========================================
    # 人格特质问卷 (Big Five)
    # ========================================
    personality = Questionnaire(
        id=str(uuid.uuid4()),
        title="🧠 人格特质评估",
        description="基于 Big Five 人格模型，通过量表评分和文字描述了解你的性格特点。",
        category="personality",
        version=1,
        order_index=1,
    )
    db.add(personality)
    db.flush()

    personality_questions = [
        {
            "content": "在社交聚会中，我通常是主动与人交谈的那个人。",
            "type": "scale", "dimension": "外向性", "order": 1,
            "min_label": "完全不符合", "max_label": "完全符合",
        },
        {
            "content": "请描述你在社交场合中的典型表现（比如：聚会、团建、陌生人社交）。",
            "type": "text", "dimension": "外向性", "order": 2,
            "placeholder": "例如：我一般会先观察环境，然后找到感兴趣的人再主动搭话...",
        },
        {
            "content": "当别人遇到困难时，我会主动提供帮助。",
            "type": "scale", "dimension": "宜人性", "order": 3,
            "min_label": "很少如此", "max_label": "总是如此",
        },
        {
            "content": "请描述你与他人发生意见冲突时，通常如何处理？",
            "type": "text", "dimension": "宜人性", "order": 4,
            "placeholder": "例如：我倾向于先听对方说完，再表达自己的看法...",
        },
        {
            "content": "我习惯提前规划日程，并按计划执行。",
            "type": "scale", "dimension": "尽责性", "order": 5,
            "min_label": "完全不符合", "max_label": "完全符合",
        },
        {
            "content": "请描述你在安排工作或学习任务时的习惯。",
            "type": "text", "dimension": "尽责性", "order": 6,
            "placeholder": "例如：我会列 TODO 清单，按优先级排序...",
        },
        {
            "content": "面对压力时，我能保持冷静和理性。",
            "type": "scale", "dimension": "情绪稳定性", "order": 7,
            "min_label": "很难做到", "max_label": "总是如此",
        },
        {
            "content": "请描述你在遇到挫折或高压时的状态和应对方式。",
            "type": "text", "dimension": "情绪稳定性", "order": 8,
            "placeholder": "例如：我会先深呼吸让自己冷静下来，然后分析问题...",
        },
        {
            "content": "我喜欢尝试新事物和新体验。",
            "type": "scale", "dimension": "开放性", "order": 9,
            "min_label": "偏好熟悉的事物", "max_label": "热衷探索新领域",
        },
        {
            "content": "请描述你对新事物（新技术、新文化、新食物等）的态度。",
            "type": "text", "dimension": "开放性", "order": 10,
            "placeholder": "例如：我对新技术很感兴趣，经常第一时间尝试...",
        },
    ]

    for q_data in personality_questions:
        q = Question(
            id=str(uuid.uuid4()),
            questionnaire_id=personality.id,
            content=q_data["content"],
            question_type=q_data["type"],
            dimension=q_data["dimension"],
            order_index=q_data["order"],
        )
        if q_data["type"] == "scale":
            q.scale_min = 1
            q.scale_max = 7
            q.scale_min_label = q_data.get("min_label", "完全不同意")
            q.scale_max_label = q_data.get("max_label", "完全同意")
        elif q_data["type"] == "text":
            q.placeholder = q_data.get("placeholder", "")
        db.add(q)

    # ========================================
    # 价值观与信念问卷
    # ========================================
    values = Questionnaire(
        id=str(uuid.uuid4()),
        title="💡 价值观与信念",
        description="了解你最看重的东西和内心的信念。",
        category="values",
        version=1,
        order_index=2,
    )
    db.add(values)
    db.flush()

    values_questions = [
        {
            "content": "以下价值观中，对你最重要的是？（可多选）",
            "type": "multi_choice", "dimension": "核心价值",
            "choices": '["家庭", "事业成就", "自由", "健康", "友情", "财富", "创造力", "社会贡献", "学习成长", "内心平静"]',
            "order": 1,
        },
        {
            "content": "如果用一句话概括你的人生信条，你会说什么？",
            "type": "text", "dimension": "人生信条", "order": 2,
            "placeholder": "例如：做自己，让别人去说吧 / 永远保持好奇心...",
        },
        {
            "content": "面对「安稳」和「冒险」，你更偏向哪一端？",
            "type": "scale", "dimension": "风险偏好", "order": 3,
            "min_label": "安稳优先", "max_label": "拥抱冒险",
        },
    ]

    for q_data in values_questions:
        q = Question(
            id=str(uuid.uuid4()),
            questionnaire_id=values.id,
            content=q_data["content"],
            question_type=q_data["type"],
            dimension=q_data["dimension"],
            order_index=q_data["order"],
        )
        if q_data["type"] == "scale":
            q.scale_min = 1
            q.scale_max = 7
            q.scale_min_label = q_data.get("min_label", "")
            q.scale_max_label = q_data.get("max_label", "")
        elif q_data["type"] == "text":
            q.placeholder = q_data.get("placeholder", "")
        elif q_data["type"] in ("choice", "multi_choice"):
            q.choices = q_data.get("choices", "[]")
        db.add(q)

    # ========================================
    # 兴趣与生活方式问卷
    # ========================================
    lifestyle = Questionnaire(
        id=str(uuid.uuid4()),
        title="🎯 兴趣与生活方式",
        description="了解你的日常偏好和长期追求。",
        category="lifestyle",
        version=1,
        order_index=3,
    )
    db.add(lifestyle)
    db.flush()

    lifestyle_questions = [
        {
            "content": "你的主要兴趣爱好有哪些？（可多选）",
            "type": "multi_choice", "dimension": "兴趣",
            "choices": '["阅读", "运动健身", "音乐", "旅行", "编程", "游戏", "美食", "摄影", "写作", "绘画", "电影", "投资理财", "户外探险", "手工制作"]',
            "order": 1,
        },
        {
            "content": "请描述你理想中的一天是什么样的。",
            "type": "text", "dimension": "生活方式", "order": 2,
            "placeholder": "从早到晚，你会怎么安排...",
        },
        {
            "content": "你目前最想实现的一个目标是什么？",
            "type": "text", "dimension": "人生目标", "order": 3,
            "placeholder": "可以是职业、个人成长、关系等任何方面...",
        },
    ]

    for q_data in lifestyle_questions:
        q = Question(
            id=str(uuid.uuid4()),
            questionnaire_id=lifestyle.id,
            content=q_data["content"],
            question_type=q_data["type"],
            dimension=q_data["dimension"],
            order_index=q_data["order"],
        )
        if q_data["type"] == "text":
            q.placeholder = q_data.get("placeholder", "")
        elif q_data["type"] in ("choice", "multi_choice"):
            q.choices = q_data.get("choices", "[]")
        db.add(q)

    # ========================================
    # 沟通偏好问卷
    # ========================================
    communication = Questionnaire(
        id=str(uuid.uuid4()),
        title="💬 沟通偏好",
        description="帮助你的数字孪生更准确地模拟你的说话方式。",
        category="communication",
        version=1,
        order_index=4,
    )
    db.add(communication)
    db.flush()

    comm_questions = [
        {
            "content": "表达观点时，你倾向于哪种方式？",
            "type": "scale", "dimension": "沟通风格", "order": 1,
            "min_label": "委婉含蓄", "max_label": "直接了当",
        },
        {
            "content": "在聊天中，你使用幽默和调侃的频率如何？",
            "type": "scale", "dimension": "幽默感", "order": 2,
            "min_label": "很少", "max_label": "经常",
        },
        {
            "content": "请用你最自然、最放松的方式，描述一下你昨天做了什么。",
            "type": "text", "dimension": "自然表达", "order": 3,
            "placeholder": "想怎么说就怎么说，就像在跟朋友聊天...",
        },
        {
            "content": "你在微信聊天时有什么口头禅或者常用的表情包类型吗？",
            "type": "text", "dimension": "表达习惯", "order": 4,
            "placeholder": "例如：哈哈哈、绝了、🐶、常用猫猫表情包...",
        },
    ]

    for q_data in comm_questions:
        q = Question(
            id=str(uuid.uuid4()),
            questionnaire_id=communication.id,
            content=q_data["content"],
            question_type=q_data["type"],
            dimension=q_data["dimension"],
            order_index=q_data["order"],
        )
        if q_data["type"] == "scale":
            q.scale_min = 1
            q.scale_max = 7
            q.scale_min_label = q_data.get("min_label", "")
            q.scale_max_label = q_data.get("max_label", "")
        elif q_data["type"] == "text":
            q.placeholder = q_data.get("placeholder", "")
        db.add(q)

    db.commit()
    total = len(onboarding_questions) + len(personality_questions) + len(values_questions) + len(lifestyle_questions) + len(comm_questions)
    print(f"✅ 种子数据已创建：5 份问卷（含引导问卷），{total} 个题目")


def main():
    config = get_config()
    init_db(config.DATABASE_URL)

    db = get_db()
    try:
        count = db.query(Questionnaire).count()
        if count == 0:
            seed_questionnaires(db)
        else:
            print(f"ℹ️ 数据库中已有 {count} 份问卷，跳过问卷初始化")
    finally:
        db.close()


if __name__ == "__main__":
    main()
