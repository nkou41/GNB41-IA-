from flask import Blueprint, jsonify
from app.models.plan import Plan

plans_bp = Blueprint('plans', __name__)


@plans_bp.route('', methods=['GET'])
def list_plans():
    plans = Plan.query.filter_by(actif=True).order_by(Plan.ordre.asc()).all()
    return jsonify({'plans': [p.to_dict() for p in plans]})
