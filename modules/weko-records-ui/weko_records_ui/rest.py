# -*- coding: utf-8 -*-
#
# This file is part of WEKO3.
# Copyright (C) 2017 National Institute of Informatics.
#
# WEKO3 is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# WEKO3 is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WEKO3; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.

"""Blueprint for schema rest."""
import inspect
import json
import re
from flask import Blueprint, current_app, jsonify, make_response, request, Response
from flask_babelex import get_locale as get_current_locale
from flask_babelex import gettext as _
from werkzeug.http import generate_etag
from invenio_oauth2server import require_api_auth, require_oauth_scopes
from invenio_pidstore.errors import PIDInvalidAction, PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_rest.links import default_links_factory
from invenio_records_rest.utils import obj_or_import_string
from invenio_records_rest.views import pass_record
from invenio_records_rest.views import \
    create_error_handlers as records_rest_error_handlers
from invenio_records_files.utils import record_file_factory
from invenio_rest import ContentNegotiatedMethodView
from invenio_rest.errors import SameContentException
from invenio_db import db
from invenio_rest.views import create_api_errorhandler
from invenio_stats.views import QueryRecordViewCount, QueryFileStatsCount
from weko_deposit.api import WekoRecord
from weko_records.serializers import citeproc_v1
from weko_items_ui.scopes import item_read_scope

from .views import escape_str
from .permissions import page_permission_factory, file_permission_factory
from .errors import VersionNotFoundRESTError, InternalServerError, \
    RecordsNotFoundRESTError, PermissionError, DateFormatRESTError, FilesNotFoundRESTError, ModeNotFoundRESTError
from .scopes import file_read_scope
from .utils import create_limmiter

limiter = create_limmiter()


def create_error_handlers(blueprint):
    """Create error handlers on blueprint."""
    blueprint.errorhandler(PIDInvalidAction)(create_api_errorhandler(
        status=403, message='Invalid action'
    ))
    records_rest_error_handlers(blueprint)


def create_blueprint(endpoints):
    """Create Weko-Records-UI-Cites-REST blueprint.

    See: :data:`invenio_deposit.config.DEPOSIT_REST_ENDPOINTS`.

    :param endpoints: List of endpoints configuration.
    :returns: The configured blueprint.
    """
    blueprint = Blueprint(
        'weko_records_ui_cites_rest',
        __name__,
        url_prefix='',
    )

    @blueprint.teardown_request
    def dbsession_clean(exception):
        current_app.logger.debug("weko_records_ui dbsession_clean: {}".format(exception))
        if exception is None:
            try:
                db.session.commit()
            except:
                db.session.rollback()
        db.session.remove()

    create_error_handlers(blueprint)

    for endpoint, options in (endpoints or {}).items():

        if 'record_serializers' in options:
            serializers = options.get('record_serializers')
            serializers = {mime: obj_or_import_string(func)
                           for mime, func in serializers.items()}
        else:
            serializers = {}

        record_class = obj_or_import_string(options['record_class'])

        ctx = dict(
            read_permission_factory=obj_or_import_string(
                options.get('read_permission_factory_imp')
            ),
            record_class=record_class,
            links_factory=obj_or_import_string(
                options.get('links_factory_imp'),
                default=default_links_factory
            ),
            # pid_type=options.get('pid_type'),
            # pid_minter=options.get('pid_minter'),
            # pid_fetcher=options.get('pid_fetcher'),
            loaders={
                options.get('default_media_type'): lambda: request.get_json()},
            default_media_type=options.get('default_media_type'),
        )

        cites = WekoRecordsCitesResource.as_view(
            WekoRecordsCitesResource.view_name.format(endpoint),
            serializers=serializers,
            # pid_type=options['pid_type'],
            ctx=ctx,
            default_media_type=options.get('default_media_type'),
        )
        blueprint.add_url_rule(
            options.get('cites_route'),
            view_func=cites,
            methods=['GET'],
        )
        wrr = WekoRecordsResource.as_view(
            WekoRecordsResource.view_name.format(endpoint),
            serializers=serializers,
            # pid_type=options['pid_type'],
            ctx=ctx,
            default_media_type=options.get('default_media_type'),
        )
        blueprint.add_url_rule(
            options.get('item_route'),
            view_func=wrr,
            methods=['GET'],
        )
        wrs = WekoRecordsStats.as_view(
            WekoRecordsStats.view_name.format(endpoint),
            serializers=serializers,
            # pid_type=options['pid_type'],
            ctx=ctx,
            default_media_type=options.get('default_media_type'),
        )
        blueprint.add_url_rule(
            options.get('records_stats_route'),
            view_func=wrs,
            methods=['GET'],
        )
        wfs = WekoFilesStats.as_view(
            WekoFilesStats.view_name.format(endpoint),
            serializers=serializers,
            # pid_type=options['pid_type'],
            ctx=ctx,
            default_media_type=options.get('default_media_type'),
        )
        blueprint.add_url_rule(
            options.get('files_stats_route'),
            view_func=wfs,
            methods=['GET'],
        )
        wfg = WekoFilesGet.as_view(
            WekoFilesGet.view_name.format(endpoint),
            serializers=serializers,
            # pid_type=options['pid_type'],
            ctx=ctx,
            default_media_type=options.get('default_media_type'),
        )
        blueprint.add_url_rule(
            options.get('files_get_route'),
            view_func=wfg,
            methods=['GET'],
        )
    return blueprint


class WekoRecordsCitesResource(ContentNegotiatedMethodView):
    """Schema files resource."""

    view_name = '{0}_cites'

    def __init__(self, serializers, ctx, *args, **kwargs):
        """Constructor."""
        super(WekoRecordsCitesResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        for key, value in ctx.items():
            setattr(self, key, value)

    # @pass_record
    # @need_record_permission('read_permission_factory')
    def get(self, pid_value, **kwargs):
        """Render citation for record according to style and language."""
        style = request.values.get('style', 1)  # style or 'science'
        locale = request.values.get('locale', 2)
        try:
            pid = PersistentIdentifier.get('depid', pid_value)
            record = WekoRecord.get_record(pid.object_uuid)
            result = citeproc_v1.serialize(pid, record, style=style,
                                           locale=locale)
            result = escape_str(result)
            return make_response(jsonify(result), 200)
        except Exception:
            current_app.logger.exception(
                'Citation formatting for record {0} failed.'.format(
                    str(record.id)))
            return make_response(jsonify("Not found"), 404)


class WekoRecordsResource(ContentNegotiatedMethodView):
    """Schema files resource."""

    view_name = '{0}_get_records'

    def __init__(self, serializers, ctx, *args, **kwargs):
        """Constructor."""
        super(WekoRecordsResource, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        for key, value in ctx.items():
            setattr(self, key, value)

    @require_api_auth(allow_anonymous=True)
    @require_oauth_scopes(item_read_scope.id)
    @limiter.limit('')
    def get(self, **kwargs):
        """Get records json."""
        version = kwargs.get('version')
        func_name = f'get_{version}'
        if func_name in [func[0] for func in inspect.getmembers(self, inspect.ismethod)]:
            return getattr(self, func_name)(**kwargs)
        else:
            raise VersionNotFoundRESTError()

    def get_v1(self, **kwargs):
        try:
            # Language setting
            language = request.headers.get('Accept-Language')
            if language == 'ja':
                get_current_locale().language = language
            elif language is None:
                language = 'en'

            # Get Record
            pid = PersistentIdentifier.get('depid', kwargs.get('pid_value'))
            record = WekoRecord.get_record(pid.object_uuid)

            # Check Permission
            if not page_permission_factory(record).can():
                raise PermissionError()

            # Convert RO-Crate format
            from .utils import RoCrateConverter
            from .models import RocrateMapping
            item_type_id = record['item_type_id']
            mapping = RocrateMapping.query.filter_by(item_type_id=item_type_id).one_or_none()
            if mapping is None:
                raise InternalServerError
            converter = RoCrateConverter()
            rocrate = converter.convert(record, mapping.mapping, language)

            # Check Etag
            etag = generate_etag(str(record).encode('utf-8'))
            self.check_etag(etag, weak=True)

            # Check Last-Modified
            last_modified = record.model.updated
            if not request.if_none_match:
                self.check_if_modified_since(dt=last_modified)

            # Check pretty
            indent = 4 if request.args.get('pretty') == 'true' else None

            # Create Response
            res_json = {
                'rocrate': rocrate,
                'metadata': self._convert_metadata(record, language),
            }
            res = Response(
                response=json.dumps(res_json, indent=indent),
                status=200,
                content_type='application/json')
            res.set_etag(etag)
            res.last_modified = last_modified

            return res

        except (PermissionError, SameContentException) as e:
            raise e

        except PIDDoesNotExistError:
            raise RecordsNotFoundRESTError()

        except Exception:
            import traceback
            print(traceback.format_exc())

            raise InternalServerError()

    def _convert_metadata(self, metadata, language):
        output = {}
        from weko_records.api import ItemTypes
        from .config import WEKO_RECORDS_UI_DISPLAY_ITEM_TYPE

        item_type = ItemTypes.get_by_id(metadata['item_type_id'])

        # Item type
        if WEKO_RECORDS_UI_DISPLAY_ITEM_TYPE:
            output[_('Item Type')] = item_type.item_type_name.name

        item_type_form = item_type.form
        target_keys = item_type.render.get('table_row')
        meta_list = item_type.render.get('meta_list')

        for property_key, property in metadata.items():
            if property_key not in target_keys:
                continue
            hidden = meta_list.get(property_key, {}).get('option', {}).get('hidden', False)
            if hidden:
                continue

            form_key = [property_key]
            form_prop = self._get_child_form(item_type_form, form_key)
            prop_value = self._get_property(property, form_prop, form_key, language)
            if not prop_value:
                continue

            title = self._get_title(form_prop, language)
            output[title] = prop_value

        return output

    def _get_property(self, record_prop, form_prop, form_key, language):
        if isinstance(record_prop, dict) and 'attribute_value_mlt' in record_prop:
            record_prop = record_prop.get('attribute_value_mlt')

        if isinstance(record_prop, str):
            return record_prop

        elif isinstance(record_prop, dict):
            output = {}
            for child_key, child_prop in record_prop.items():
                if 'items' not in form_prop:
                    continue
                child_form_key = form_key + [child_key]
                child_form_prop = self._get_child_form(form_prop.get('items'), child_form_key)
                if 'isHide' in child_form_prop and child_form_prop.get('isHide'):
                    continue
                if not child_form_prop:
                    continue
                title = self._get_title(child_form_prop, language)
                if not title:
                    continue
                child_prop_value = self._get_property(child_prop, child_form_prop, child_form_key, language)
                if not child_prop_value:
                    continue
                output[title] = child_prop_value
            return output

        elif isinstance(record_prop, list):
            output = []
            for child_record_prop in record_prop:
                child_prop_value = self._get_property(child_record_prop, form_prop, form_key, language)
                if not child_prop_value:
                    continue
                output.append(child_prop_value)
            return output

    def _get_title(self, form_prop, language):
        if 'title_i18n' in form_prop:
            title_i18n = form_prop.get('title_i18n')
            if language in title_i18n:
                return title_i18n.get(language)
        return form_prop.get('title', '')

    def _get_child_form(self, child_forms, child_key):
        target = {}
        for child_form in child_forms:
            if 'key' not in child_form:
                continue
            if self._check_form_key(child_form['key'], child_key):
                target = child_form
                break
        return target

    def _check_form_key(self, form_key, child_key):
        form_keys = form_key.split('.')
        if len(form_keys) != len(child_key):
            return False
        for index, key_name in enumerate(form_keys):
            key_name = key_name.split('[')[0]
            if child_key[index] != key_name:
                return False
        return True


class WekoRecordsStats(ContentNegotiatedMethodView):
    """Schema Records resource."""

    view_name = '{0}_get_records_stats'

    def __init__(self, serializers, ctx, *args, **kwargs):
        """Constructor."""
        super(WekoRecordsStats, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        for key, value in ctx.items():
            setattr(self, key, value)

    @require_api_auth(allow_anonymous=True)
    @require_oauth_scopes(item_read_scope.id)
    @limiter.limit('')
    def get(self, **kwargs):
        """Get record stats."""
        version = kwargs.get('version')
        func_name = f'get_{version}'
        if func_name in [func[0] for func in inspect.getmembers(self, inspect.ismethod)]:
            return getattr(self, func_name)(**kwargs)
        else:
            raise VersionNotFoundRESTError()

    def get_v1(self, **kwargs):
        try:
            # Get object_uuid by pid_value
            pid = PersistentIdentifier.get('depid', kwargs.get('pid_value'))
            record = WekoRecord.get_record(pid.object_uuid)

            # Check Permission
            if not page_permission_factory(record).can():
                raise PermissionError()

            # Get date param
            date = request.values.get('date', type=str)

            # Check date pattern
            if date:
                date = re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', date)
                if not date:
                    raise DateFormatRESTError()
                date = date.group()

            # Get target class
            query_record_stats = QueryRecordViewCount()
            result = query_record_stats.get_data(pid.object_uuid, date)

            if date:
                result['period'] = date
            else:
                result['period'] = 'total'

            # Check Etag
            etag = generate_etag(str(record).encode('utf-8'))
            self.check_etag(etag, weak=True)

            # Check pretty
            indent = 4 if request.args.get('pretty') == 'true' else None

            # Create Response
            res = Response(
                response=json.dumps(result, indent=indent),
                status=200,
                content_type='application/json')
            res.set_etag(etag)

            return res

        except (PermissionError, DateFormatRESTError, SameContentException) as e:
            raise e

        except PIDDoesNotExistError:
            raise RecordsNotFoundRESTError()

        except Exception:
            raise InternalServerError()


class WekoFilesStats(ContentNegotiatedMethodView):
    """Schema files resource."""

    view_name = '{0}_get_files_stats'

    def __init__(self, serializers, ctx, *args, **kwargs):
        """Constructor."""
        super(WekoFilesStats, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        for key, value in ctx.items():
            setattr(self, key, value)

    @require_api_auth(allow_anonymous=True)
    @require_oauth_scopes(file_read_scope.id)
    @limiter.limit('')
    def get(self, **kwargs):
        """Get file stats."""
        version = kwargs.get('version')
        func_name = f'get_{version}'
        if func_name in [func[0] for func in inspect.getmembers(self, inspect.ismethod)]:
            return getattr(self, func_name)(**kwargs)
        else:
            raise VersionNotFoundRESTError()

    def get_v1(self, **kwargs):
        try:
            from weko_items_ui.config import WEKO_ITEMS_UI_MS_MIME_TYPE, WEKO_ITEMS_UI_FILE_SISE_PREVIEW_LIMIT

            # Get object_uuid by pid_value
            pid = PersistentIdentifier.get('recid', kwargs.get('pid_value'))
            record = WekoRecord.get_record(pid.object_uuid)

            # Check record permission
            if not page_permission_factory(record).can():
                raise PermissionError()

            # Check file exist
            current_app.config['WEKO_ITEMS_UI_MS_MIME_TYPE'] = WEKO_ITEMS_UI_MS_MIME_TYPE
            current_app.config['WEKO_ITEMS_UI_FILE_SISE_PREVIEW_LIMIT'] = WEKO_ITEMS_UI_FILE_SISE_PREVIEW_LIMIT
            fileobj = record_file_factory(pid, record, kwargs.get('filename'))
            if not fileobj:
                raise FilesNotFoundRESTError()

            # Check file contents permission
            if not file_permission_factory(record, fjson=fileobj).can():
                raise PermissionError()

            # Get date param
            date = request.values.get('date', type=str)

            # Check date pattern
            if date:
                date = re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', date)
                if not date:
                    raise DateFormatRESTError()
                date = date.group()

            query_record_stats = QueryFileStatsCount()
            result = query_record_stats.get_data(pid.object_uuid, kwargs.get('filename'), date)
            if date:
                result['period'] = date
            else:
                result['period'] = 'total'

            # Check Etag
            etag = generate_etag(str(record).encode('utf-8'))
            self.check_etag(etag, weak=True)

            # Check pretty
            indent = 4 if request.args.get('pretty') == 'true' else None

            # Create Response
            res = Response(
                response=json.dumps(result, indent=indent),
                status=200,
                content_type='application/json')
            res.set_etag(etag)

            return res

        except (PermissionError, FilesNotFoundRESTError, DateFormatRESTError, SameContentException) as e:
            raise e

        except PIDDoesNotExistError:
            raise RecordsNotFoundRESTError()

        except Exception:
            raise InternalServerError()


class WekoFilesGet(ContentNegotiatedMethodView):
    """Schema files resource."""

    view_name = '{0}_get_files'

    def __init__(self, serializers, ctx, *args, **kwargs):
        """Constructor."""
        super(WekoFilesGet, self).__init__(
            serializers,
            *args,
            **kwargs
        )
        for key, value in ctx.items():
            setattr(self, key, value)

    @require_api_auth(allow_anonymous=True)
    @require_oauth_scopes(file_read_scope.id)
    @limiter.limit('')
    def get(self, **kwargs):
        """Get file."""
        version = kwargs.get('version')
        func_name = f'get_{version}'
        if func_name in [func[0] for func in inspect.getmembers(self, inspect.ismethod)]:
            return getattr(self, func_name)(**kwargs)
        else:
            raise VersionNotFoundRESTError()

    def get_v1(self, **kwargs):
        try:
            from weko_items_ui.config import WEKO_ITEMS_UI_MS_MIME_TYPE, WEKO_ITEMS_UI_FILE_SISE_PREVIEW_LIMIT

            # Get record
            pid = PersistentIdentifier.get('recid', kwargs.get('pid_value'))
            record = WekoRecord.get_record(pid.object_uuid)

            # Check record permission
            if not page_permission_factory(record).can():
                raise PermissionError()

            # Check mode
            mode = request.values.get('mode', '')
            if mode == '' or mode == 'download':
                is_preview = False
            elif mode == 'preview':
                is_preview = True
            else:
                raise ModeNotFoundRESTError()

            # Check file exist
            current_app.config['WEKO_ITEMS_UI_MS_MIME_TYPE'] = WEKO_ITEMS_UI_MS_MIME_TYPE
            current_app.config['WEKO_ITEMS_UI_FILE_SISE_PREVIEW_LIMIT'] = WEKO_ITEMS_UI_FILE_SISE_PREVIEW_LIMIT
            fileObj = record_file_factory(pid, record, kwargs.get('filename'))
            if not fileObj:
                raise FilesNotFoundRESTError()

            # Check file contents permission
            if not file_permission_factory(record, fjson=fileObj).can():
                raise PermissionError()

            # Get File Request
            current_app.config['WEKO_ITEMS_UI_MS_MIME_TYPE'] = WEKO_ITEMS_UI_MS_MIME_TYPE
            current_app.config['WEKO_ITEMS_UI_FILE_SISE_PREVIEW_LIMIT'] = WEKO_ITEMS_UI_FILE_SISE_PREVIEW_LIMIT
            from .fd import file_ui
            dl_response = file_ui(pid, record, is_preview=is_preview, **kwargs)

            # Check Etag
            hash_str = str(record) + mode + kwargs.get('filename')
            etag = generate_etag(hash_str.encode('utf-8'))
            self.check_etag(etag, weak=True)

            # Check Last-Modified
            last_modified = record.model.updated
            if not request.if_none_match:
                self.check_if_modified_since(dt=last_modified)

            content_type = fileObj.mimetype
            if is_preview:
                if 'msword' in fileObj.mimetype or 'vnd.ms' in fileObj.mimetype or 'vnd.openxmlformats' in fileObj.mimetype:
                    if fileObj.data.get('displaytype') == 'preview':
                        content_type = 'application/pdf'

            # Response Header Setting
            dl_response.set_etag(etag)
            dl_response.last_modified = last_modified
            dl_response.content_type = content_type

            return dl_response

        except (ModeNotFoundRESTError, FilesNotFoundRESTError, PermissionError, SameContentException) as e:
            raise e

        except PIDDoesNotExistError:
            raise RecordsNotFoundRESTError()

        except Exception:
            raise InternalServerError()
