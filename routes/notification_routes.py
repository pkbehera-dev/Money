from flask import Blueprint, jsonify, request
from services.notification_service import NotificationService

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/api/notifications')
def get_notifications():
    unread_only = request.args.get('unread') == 'true'
    notifications = NotificationService.get_notifications(unread_only)
    return jsonify(notifications)

@notification_bp.route('/api/notifications/read/<int:n_id>', methods=['POST'])
def mark_read(n_id):
    NotificationService.mark_as_read(n_id)
    return jsonify({"status": "success"})

@notification_bp.route('/api/notifications/<int:n_id>', methods=['DELETE'])
def delete_notification(n_id):
    NotificationService.delete_notification(n_id)
    return jsonify({"status": "success"})

@notification_bp.route('/api/notifications/check', methods=['POST'])
def force_check():
    NotificationService.check_all_triggers()
    return jsonify({"status": "checked"})
