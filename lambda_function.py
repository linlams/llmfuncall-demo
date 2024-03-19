import json
import os
from pydantic import BaseModel, validator, ValidationError
from typing import Optional
from sqlalchemy import create_engine, text, Column, Integer, String, MetaData, Table, Sequence, or_, and_
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session
import difflib

db_username = os.environ.get('db_username')
db_password = os.environ.get('db_password')
db_host = os.environ.get('db_host')
db_port = os.environ.get('db_port')
db_name = os.environ.get('db_name')
db_table_name = os.environ.get('db_table_name')
similarity_threshold = os.environ.get('similarity_threshold', 0.4)

new_db_connection_string = f"mysql+pymysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
new_db_engine = create_engine(new_db_connection_string)

Base = declarative_base()
session = Session(bind=new_db_engine)


# 定义模型类，需要根据数据修改
class Visa_SQLAlchemy(Base):
    __tablename__ = db_table_name
    country = Column(String(50), primary_key=True)
    continent = Column(String(50), nullable=True)
    visa_requirement = Column(String(100), nullable=True)
    e_visa = Column(String(50), nullable=True)
    policy = Column(String(255), nullable=True)
    policy_url = Column(String(255), nullable=True)
    regulation = Column(String(255), nullable=True)


class Visa_Pydantic(BaseModel):
    country: Optional[str] = None
    continent: Optional[str] = None
    visa_requirement: Optional[str] = None
    e_visa: Optional[str] = None
    policy: Optional[str] = None
    policy_url: Optional[str] = None
    regulation: Optional[str] = None

#############################################


def lambda_handler(event, context):
    param = event.get('param')
    query = event.get('query', None)

    visa_obj = None
    try:
        visa_obj = Visa_Pydantic(**param)
    except ValidationError as e:
        return {
            'statusCode': 500,
            'message': e.json()
        }

    visa_sql = Visa_SQLAlchemy(**visa_obj.dict())

    def format_results(results):
        converted_items = []

        for idx, item in enumerate(results):
            e_visa_in_set = '支持电子签' if item.international_can_set == '支持电子签' else '不支持电子签'
            converted_items.append(
                f"[{idx + 1}] {item.country} 签证签证类型为：{item.visa_requirement} , {e_visa_in_set} ,相关政策：{item.policy},政策URL：{item.policy_url}, 其他规定：{item.regulation}")


        return converted_items

    def possible_candidates_by_diff(records, input_str, ret_cnt=3):
        sim_list = []
        for record in records:
            print(f"input_str:{input_str}")
            print(f"record:{record}")
            similarity = difflib.SequenceMatcher(None, input_str, record[0]).ratio()
            sim_list.append((record[0], similarity))

        sorted_sim_list = sorted(sim_list, key=lambda x: x[1], reverse=True)
        print(f"sorted_sim_list:{sorted_sim_list}")
        return [item[0] for item in sorted_sim_list[:ret_cnt] if item[1] > similarity_threshold]

    suggested_question = ""
    code = 200
    if visa_sql.country is not None:
        print("query by employee name")
        results = session.query(Visa_SQLAlchemy).filter(
            Visa_SQLAlchemy.flightno.ilike(f'%{visa_sql.flightno}%')).all()
        if len(results) == 0:
            message = f"无法找到签证信息- {visa_sql.country}."
            all_possible_flights = session.query(Visa_SQLAlchemy.flightno).all()
            top_similar_objs = possible_candidates_by_diff(all_possible_flights, visa_sql.flightno)
            if len(top_similar_objs) > 1 and query:
                code = 404
                suggested_question = query.replace(visa_sql.flightno, top_similar_objs[0])
        else:
            message = format_results(results)

    else:
        message = "Can't find relevant information."

    return {
        'statusCode': code,
        'message': message,
        'suggested_question': suggested_question
    }