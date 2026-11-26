from flask import Blueprint, send_file, Response, abort, request
from utils.db import get_fs
from bson.objectid import ObjectId
import io

file_serving_bp = Blueprint('file_serving', __name__)

@file_serving_bp.route('/files/<file_id>')
def serve_file(file_id):
    fs = get_fs()
    try:
        if not ObjectId.is_valid(file_id):
            abort(404)
            
        file_obj = fs.get(ObjectId(file_id))
        
        # Determine content type based on filename extension (basic) or metadata
        filename = file_obj.filename or 'download'
        content_type = getattr(file_obj, 'content_type', None) or 'application/octet-stream'
        
        if filename.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        elif filename.lower().endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        elif filename.lower().endswith('.png'):
            content_type = 'image/png'
        elif filename.lower().endswith('.webp'):
            content_type = 'image/webp'
            
        return send_file(
            io.BytesIO(file_obj.read()),
            mimetype=content_type,
            as_attachment=True,
            download_name=filename
        )
    except Exception:
        abort(404)

@file_serving_bp.route('/files/view/<file_id>')
def view_file_inline(file_id):
    """Serve file inline for browser rendering (images, previews)"""
    fs = get_fs()
    try:
        if not ObjectId.is_valid(file_id):
            abort(404)
            
        file_obj = fs.get(ObjectId(file_id))
        filename = file_obj.filename or 'file'
        content_type = getattr(file_obj, 'content_type', None) or 'application/octet-stream'
        
        if filename.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        elif filename.lower().endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        elif filename.lower().endswith('.png'):
            content_type = 'image/png'
        elif filename.lower().endswith('.webp'):
            content_type = 'image/webp'
        elif filename.lower().endswith('.gif'):
            content_type = 'image/gif'
            
        etag = f'"{file_id}"'
        if request.headers.get('If-None-Match') == etag:
            return Response('', status=304, headers={
                'ETag': etag,
                'Cache-Control': 'public, max-age=604800, immutable'
            })

        resp = send_file(
            io.BytesIO(file_obj.read()),
            mimetype=content_type,
            as_attachment=False
        )
        resp.headers['ETag'] = etag
        resp.headers['Cache-Control'] = 'public, max-age=604800, immutable'
        return resp
    except Exception:
        abort(404)
