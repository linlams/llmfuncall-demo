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
class Airline_SQLAlchemy(Base):
    __tablename__ = db_table_name
    id = Column(Integer, primary_key=True, autoincrement=True)
    flightno = Column(String(32), nullable=True)
    callname = Column(String(128), nullable=True)
    domestic_setting = Column(String(128), nullable=True)
    international_can_set = Column(String(32), nullable=True)
    international_online_set = Column(String(32), nullable=True)
    baoshen_can_set = Column(String(32), nullable=True)
    domestic_license = Column(String(128), nullable=True)


class Airline_Pydantic(BaseModel):
    flightno: Optional[str] = None
    callname: Optional[str] = None
    domestic_setting: Optional[str] = None
    international_can_set: Optional[str] = None
    international_online_set: Optional[str] = None
    baoshen_can_set: Optional[str] = None
    domestic_license: Optional[str] = None

#############################################


def lambda_handler(event, context):
    param = event.get('param')
    query = event.get('query', None)

    airline_obj = None
    try:
        airline_obj = Airline_Pydantic(**param)
    except ValidationError as e:
        return {
            'statusCode': 500,
            'message': e.json()
        }

    airline_sql = Airline_SQLAlchemy(**airline_obj.dict())

    def format_results(results):
        converted_items = []

        for idx, item in enumerate(results):
            in_set = '可以' if item.international_can_set == '是' else '不可以'
            online_set = '可以' if item.international_online_set == '是' else '不可以'
            baoshen_set = '可以' if item.baoshen_can_set == '是' else '不可以'
            converted_items.append(
                f"[{idx + 1}] 航司 {item.flightno} 有这些紧密关联的信息。它称谓规则请从如下json总结：<json>{item.callname}<json>, "
                f"它的国内预定配置信息请从如下json总结：<json>{item.domestic_setting} <json>，"
                f"航司 {item.flightno} 在国际{in_set}预定，"
                f"航司 {item.flightno} 在境外 {online_set} 电子预定，"
                f"航司 {item.flightno} 通过保盛 {baoshen_set} 预定")

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
    if airline_sql.flightno is not None:
        print("query by employee name")
        results = session.query(Airline_SQLAlchemy).filter(
            Airline_SQLAlchemy.flightno.ilike(f'%{airline_sql.flightno}%')).all()
        if len(results) == 0:
            message = f"无法找到航司- {airline_sql.flightno}."
            all_possible_flights = session.query(Airline_SQLAlchemy.flightno).all()
            top_similar_objs = possible_candidates_by_diff(all_possible_flights, airline_sql.flightno)
            if len(top_similar_objs) > 1 and query:
                code = 404
                suggested_question = query.replace(airline_sql.flightno, top_similar_objs[0])
        else:
            message = format_results(results)

    else:
        message = "Can't find relevant information."

    return {
        'statusCode': code,
        'message': message,
        'suggested_question': suggested_question
    }
