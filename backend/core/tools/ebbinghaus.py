"""
艾宾浩斯遗忘曲线计算工具
根据艾宾浩斯记忆周期计算下次复习日期
"""
from datetime import date, timedelta
from backend.config import EBBINGHAUS_INTERVALS


class EbbinghausCalculator:
    """
    艾宾浩斯遗忘曲线计算器

    标准复习间隔（天）：0, 1, 2, 4, 7, 15, 30, 60, 120
    - stage 0：学习当天（间隔0天）
    - stage 1：第1天后
    - stage 2：第2天后
    - ...
    - stage 8：第120天后（约4个月，基本进入长期记忆）

    每次复习后，根据结果决定升级/降级/保持当前阶段
    """

    STAGE_INTERVALS = EBBINGHAUS_INTERVALS  # 共9个阶段

    @classmethod
    def get_next_review_date(cls, stage: int, from_date: date | None = None) -> date:
        """
        根据当前阶段计算下次复习日期
        :param stage: 当前艾宾浩斯阶段（0-8）
        :param from_date: 计算起点日期，默认今天
        :return: 下次复习日期
        """
        if stage < 0:
            stage = 0
        if stage >= len(cls.STAGE_INTERVALS):
            # 已过所有阶段，进入稳定长期记忆（90天后复习）
            return (from_date or date.today()) + timedelta(days=90)

        interval = cls.STAGE_INTERVALS[stage]
        return (from_date or date.today()) + timedelta(days=interval)

    @classmethod
    def get_review_schedule(cls, start_date: date, total_stages: int | None = None) -> list[dict]:
        """
        生成完整的复习日程表
        :param start_date: 学习开始日期
        :param total_stages: 总共几个阶段，默认全部
        :return: [{stage, date, description}, ...]
        """
        stages = total_stages or len(cls.STAGE_INTERVALS)
        schedule = []
        for i in range(stages):
            review_date = start_date + timedelta(days=cls.STAGE_INTERVALS[i])
            descriptions = [
                "当日首次学习",
                "第1天复习",
                "第2天复习",
                "第4天复习",
                "第7天复习",
                "第15天复习",
                "第30天复习",
                "第60天复习",
                "第120天复习（长期巩固）",
            ]
            schedule.append({
                "stage": i,
                "interval_days": cls.STAGE_INTERVALS[i],
                "review_date": review_date.isoformat(),
                "description": descriptions[i] if i < len(descriptions) else f"第{cls.STAGE_INTERVALS[i]}天复习",
            })
        return schedule

    @classmethod
    def calc_next_stage(cls, current_stage: int, is_correct: bool) -> tuple[int, date]:
        """
        根据复习结果计算下一个阶段
        :param current_stage: 当前阶段
        :param is_correct: 本次复习是否正确
        :return: (下一阶段, 下次复习日期)
        """
        if is_correct:
            # 正确 → 阶段升级
            new_stage = min(current_stage + 1, len(cls.STAGE_INTERVALS) - 1)
        else:
            # 错误 → 阶段降级（最多降2级，不低于0）
            new_stage = max(current_stage - 2, 0)

        next_date = cls.get_next_review_date(new_stage)
        return new_stage, next_date

    @classmethod
    def get_due_review_words(cls, study_records: list, as_of: date | None = None) -> list:
        """
        筛选当前待复习的单词
        :param study_records: 学习记录列表
        :param as_of: 截止日期
        :return: 需要今日复习的记录
        """
        today = as_of or date.today()
        due = []
        for record in study_records:
            if record.next_review and record.next_review <= today:
                due.append(record)
        return due

    @classmethod
    def get_new_words_count(cls, daily_target: int, review_count: int) -> int:
        """
        每日新词始终等于用户设定的目标数量，不因复习量而减少。
        复习是独立任务，与新词学习并行，互不挤压。
        随着词库学完，新词自然减少（池子干了就没了）。
        """
        return daily_target
