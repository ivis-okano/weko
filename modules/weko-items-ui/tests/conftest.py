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

"""Pytest configuration."""

import shutil
import tempfile
import os
import json
import uuid
from datetime import datetime
from os.path import dirname, exists, join
import pytest
from flask import Flask,Blueprint
from flask_babelex import Babel
from flask_menu import Menu
from invenio_accounts import InvenioAccounts
from invenio_accounts.views.settings import \
    blueprint as invenio_accounts_blueprint
from invenio_accounts.testutils import create_test_user, login_user_via_session
from weko_user_profiles.models import UserProfile
from invenio_access import InvenioAccess
from invenio_access.models import ActionUsers,ActionRoles
from invenio_accounts.models import User, Role
from sqlalchemy_utils.functions import create_database, database_exists

from invenio_db import InvenioDB
from invenio_db import db as db_

from invenio_communities import InvenioCommunities
from weko_workflow import WekoWorkflow
from weko_items_ui import WekoItemsUI
from invenio_i18n import InvenioI18N
from invenio_cache import InvenioCache
from invenio_admin import InvenioAdmin
from invenio_theme import InvenioTheme
from invenio_deposit import InvenioDeposit
from weko_theme.views import blueprint as weko_theme_blueprint
from invenio_admin.views import blueprint as invenio_admin_blueprint
from invenio_db import InvenioDB, db as db_
from invenio_stats import InvenioStats
from invenio_assets import InvenioAssets
from weko_items_ui.views import blueprint as weko_items_ui_blueprint
from weko_items_ui.views import blueprint_api as weko_items_ui_blueprint_api
from weko_records.models import ItemTypeName, ItemType,ItemTypeMapping
from weko_workflow import WekoWorkflow
from invenio_search import RecordsSearch
from weko_workflow.views import blueprint as weko_workflow_blueprint
from weko_workflow.models import Activity, ActionStatus, Action, WorkFlow, FlowDefine, FlowAction
from invenio_communities.views.ui import blueprint as invenio_communities_blueprint
from click.testing import CliRunner
from invenio_assets.cli import collect
from flask_assets import assets
from invenio_assets.cli import npm
from invenio_rest import InvenioREST
from weko_records import WekoRecords
from invenio_pidrelations import InvenioPIDRelations
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_pidstore.models import PersistentIdentifier, PIDStatus, Redirect
from weko_deposit import WekoDeposit
from invenio_records_rest import InvenioRecordsREST
from invenio_jsonschemas import InvenioJSONSchemas
from invenio_search import InvenioSearch
from weko_schema_ui.models import OAIServerSchema
from invenio_oaiserver import InvenioOAIServer
from invenio_indexer import InvenioIndexer
from weko_records_ui import WekoRecordsUI
from weko_theme import WekoTheme
from weko_admin import WekoAdmin
from weko_admin.models import SessionLifetime 
from tests.helpers import json_data, create_record
from werkzeug.local import LocalProxy

from invenio_files_rest.models import Location
from invenio_files_rest import InvenioFilesREST
from weko_search_ui import WekoSearchUI,WekoSearchREST
from weko_index_tree import WekoIndexTree
from weko_records import WekoRecords
from invenio_stats.config import SEARCH_INDEX_PREFIX as index_prefix
from weko_records_ui.config import WEKO_RECORDS_UI_LICENSE_DICT


# from sqlalchemy.engine import Engine
# from sqlalchemy.orm import Session
# from sqlalchemy import event

# @event.listens_for(Engine, "connect")
# def set_sqlite_pragma(dbapi_connection, connection_record):
#     cursor = dbapi_connection.cursor()
#     cursor.execute("PRAGMA foreign_keys=OFF;")
#     cursor.close()

# @event.listens_for(Session, 'after_begin')
# def receive_after_begin(session, transaction, connection):
#     connection.execute("PRAGMA foreign_keys=OFF;")

@pytest.yield_fixture()
def instance_path():
    """Temporary instance path."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture()
def base_app(instance_path):
    """Flask application fixture."""
    app_ = Flask('testapp', instance_path=instance_path,static_folder=join(instance_path, "static"))
    app_.config.update(
        SECRET_KEY='SECRET_KEY',
        TESTING=True,
        SERVER_NAME='test_server',
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        ACCOUNTS_USERINFO_HEADERS=True,
        WEKO_PERMISSION_SUPER_ROLE_USER=['System Administrator',
                                         'Repository Administrator'],
        WEKO_PERMISSION_ROLE_COMMUNITY=['Community Administrator'],
        THEME_SITEURL = 'https://localhost',
        WEKO_THEME_DEFAULT_COMMUNITY="Root Index",
        #  WEKO_ITEMS_UI_BASE_TEMPLATE = 'weko_items_ui/base.html',
        #  WEKO_ITEMS_UI_INDEX_TEMPLATE= 'weko_items_ui/item_index.html',
        CACHE_TYPE = 'redis' ,
        ACCOUNTS_SESSION_REDIS_DB_NO = 1,
        CACHE_REDIS_HOST = os.environ.get('INVENIO_REDIS_HOST'),
        REDIS_PORT = '6379',
        WEKO_BUCKET_QUOTA_SIZE = 50 * 1024 * 1024 * 1024,
        WEKO_MAX_FILE_SIZE = 50 * 1024 * 1024 * 1024,
        SEARCH_ELASTIC_HOSTS = os.environ.get('INVENIO_ELASTICSEARCH_HOST'),
SEARCH_INDEX_PREFIX = os.environ.get('SEARCH_INDEX_PREFIX'),
SEARCH_CLIENT_CONFIG = dict(timeout=60, max_retries=5),
        OAISERVER_ID_PREFIX='oai:inveniosoftware.org:recid/',
        OAISERVER_RECORD_INDEX='_all',
        OAISERVER_REGISTER_SET_SIGNALS=True,
        OAISERVER_METADATA_FORMATS = {
            'jpcoar_1.0': {
            'serializer': (
                'weko_schema_ui.utils:dumps_oai_etree', {
                    'schema_type': 'jpcoar_v1',
                }
            ),
            'namespace': 'https://irdb.nii.ac.jp/schema/jpcoar/1.0/',
            'schema': 'https://irdb.nii.ac.jp/schema/jpcoar/1.0/jpcoar_scm.xsd',
            }
        },
        WEKO_RECORDS_UI_LICENSE_DICT=WEKO_RECORDS_UI_LICENSE_DICT
    )
    # Babel(app_)
    InvenioI18N(app_)
    InvenioTheme(app_)
    InvenioREST(app_)
    InvenioAccess(app_)
    InvenioAccounts(app_)
    InvenioCache(app_)
    InvenioDB(app_)
    InvenioDeposit(app_)
    InvenioPIDStore(app_)
    InvenioPIDRelations(app_)
    InvenioRecords(app_)
    InvenioRecordsREST(app_)
    InvenioFilesREST(app_)
    InvenioJSONSchemas(app_)
    InvenioOAIServer(app_)
    InvenioIndexer(app_)
    InvenioSearch(app_)
    # InvenioStats(app_)
    
    InvenioAdmin(app_)
    # Menu(app_)
    WekoDeposit(app_)
    WekoWorkflow(app_)
    WekoAdmin(app_)
    WekoTheme(app_)
    WekoRecordsUI(app_)
    InvenioCommunities(app_)
    InvenioAssets(app_)
    
    # WekoSearchREST(app_)
    # WekoIndexTree(app_)
    WekoRecords(app_)
    # WekoSearchUI(app_)
    # ext.init_config(app_)
    WekoItemsUI(app_)
    # app_.register_blueprint(invenio_accounts_blueprint)
    # app_.register_blueprint(weko_theme_blueprint)
    # app_.register_blueprint(weko_items_ui_blueprint)
    # app_.register_blueprint(invenio_communities_blueprint)
    # app_.register_blueprint(weko_workflow_blueprint)

    # runner = CliRunner()
    # result = runner.invoke(collect, [],obj=weko_items_ui_blueprint)
    # Run build
    # result = runner.invoke(assets, ['build'],obj=weko_items_ui_blueprint)
    # result = runner.invoke(npm,obj=weko_items_ui_blueprint)

    
    current_assets = LocalProxy(lambda: app_.extensions["invenio-assets"])
    current_assets.collect.collect()
    return app_


@pytest.yield_fixture()
def app(base_app):
    """Flask application fixture."""
    with base_app.app_context():
        yield base_app


@pytest.yield_fixture()
def client_api(app):
    app.register_blueprint(weko_items_ui_blueprint_api, url_prefix="/api/items")
    with app.test_client() as client:
        yield client

@pytest.yield_fixture()
def client(app):
    """make a test client.

    Args:
        app (Flask): flask app.

    Yields:
        FlaskClient: test client
    """
    app.register_blueprint(weko_items_ui_blueprint,url_prefix="/items")
    with app.test_client() as client:
        yield client

@pytest.fixture()
def db(app):
    """Database fixture."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.fixture()
def users(app, db):
    """Create users."""
    ds = app.extensions['invenio-accounts'].datastore
    user_count = User.query.filter_by(email='user@test.org').count()
    if user_count != 1:
        user = create_test_user(email='user@test.org')
        contributor = create_test_user(email='contributor@test.org')
        comadmin = create_test_user(email='comadmin@test.org')
        repoadmin = create_test_user(email='repoadmin@test.org')
        sysadmin = create_test_user(email='sysadmin@test.org')
        generaluser = create_test_user(email='generaluser@test.org')
        originalroleuser = create_test_user(email='originalroleuser@test.org')
        originalroleuser2 = create_test_user(email='originalroleuser2@test.org')
    else:
        user = User.query.filter_by(email='user@test.org').first()
        contributor = User.query.filter_by(email='contributor@test.org').first()
        comadmin = User.query.filter_by(email='comadmin@test.org').first()
        repoadmin = User.query.filter_by(email='repoadmin@test.org').first()
        sysadmin = User.query.filter_by(email='sysadmin@test.org').first()
        generaluser = User.query.filter_by(email='generaluser@test.org')
        originalroleuser = create_test_user(email='originalroleuser@test.org')
        originalroleuser2 = create_test_user(email='originalroleuser2@test.org')

    role_count = Role.query.filter_by(name='System Administrator').count()
    if role_count != 1:
        sysadmin_role = ds.create_role(name='System Administrator')
        repoadmin_role = ds.create_role(name='Repository Administrator')
        contributor_role = ds.create_role(name='Contributor')
        comadmin_role = ds.create_role(name='Community Administrator')
        general_role = ds.create_role(name='General')
        originalrole = ds.create_role(name='Original Role')
    else:
        sysadmin_role = Role.query.filter_by(name='System Administrator').first()
        repoadmin_role = Role.query.filter_by(name='Repository Administrator').first()
        contributor_role = Role.query.filter_by(name='Contributor').first()
        comadmin_role = Role.query.filter_by(name='Community Administrator').first()
        general_role = Role.query.filter_by(name='General').first()
        originalrole = Role.query.filter_by(name='Original Role').first()

    ds.add_role_to_user(sysadmin, sysadmin_role)
    ds.add_role_to_user(repoadmin, repoadmin_role)
    ds.add_role_to_user(contributor, contributor_role)
    ds.add_role_to_user(comadmin, comadmin_role)
    ds.add_role_to_user(generaluser, general_role)
    ds.add_role_to_user(originalroleuser, originalrole)
    ds.add_role_to_user(originalroleuser2, originalrole)
    ds.add_role_to_user(originalroleuser2, repoadmin_role)
    
    # Assign access authorization
    with db.session.begin_nested():
        action_users = [
            ActionUsers(action='superuser-access', user=sysadmin),
        ]
        db.session.add_all(action_users)
        action_roles = [
            ActionRoles(action='superuser-access', role=sysadmin_role),
            ActionRoles(action='admin-access', role=repoadmin_role),
            ActionRoles(action='schema-access', role=repoadmin_role),
            ActionRoles(action='index-tree-access', role=repoadmin_role),
            ActionRoles(action='indextree-journal-access', role=repoadmin_role),
            ActionRoles(action='item-type-access', role=repoadmin_role),
            ActionRoles(action='item-access', role=repoadmin_role),
            ActionRoles(action='files-rest-bucket-update', role=repoadmin_role),
            ActionRoles(action='files-rest-object-delete', role=repoadmin_role),
            ActionRoles(action='files-rest-object-delete-version', role=repoadmin_role),
            ActionRoles(action='files-rest-object-read', role=repoadmin_role),
            ActionRoles(action='search-access', role=repoadmin_role),
            ActionRoles(action='detail-page-acces', role=repoadmin_role),
            ActionRoles(action='download-original-pdf-access', role=repoadmin_role),
            ActionRoles(action='author-access', role=repoadmin_role),
            ActionRoles(action='items-autofill', role=repoadmin_role),
            ActionRoles(action='stats-api-access', role=repoadmin_role),
            ActionRoles(action='read-style-action', role=repoadmin_role),
            ActionRoles(action='update-style-action', role=repoadmin_role),
            ActionRoles(action='detail-page-acces', role=repoadmin_role),

            ActionRoles(action='admin-access', role=comadmin_role),
            ActionRoles(action='index-tree-access', role=comadmin_role),
            ActionRoles(action='indextree-journal-access', role=comadmin_role),
            ActionRoles(action='item-access', role=comadmin_role),
            ActionRoles(action='files-rest-bucket-update', role=comadmin_role),
            ActionRoles(action='files-rest-object-delete', role=comadmin_role),
            ActionRoles(action='files-rest-object-delete-version', role=comadmin_role),
            ActionRoles(action='files-rest-object-read', role=comadmin_role),
            ActionRoles(action='search-access', role=comadmin_role),
            ActionRoles(action='detail-page-acces', role=comadmin_role),
            ActionRoles(action='download-original-pdf-access', role=comadmin_role),
            ActionRoles(action='author-access', role=comadmin_role),
            ActionRoles(action='items-autofill', role=comadmin_role),
            ActionRoles(action='detail-page-acces', role=comadmin_role),
            ActionRoles(action='detail-page-acces', role=comadmin_role),

            ActionRoles(action='item-access', role=contributor_role),
            ActionRoles(action='files-rest-bucket-update', role=contributor_role),
            ActionRoles(action='files-rest-object-delete', role=contributor_role),
            ActionRoles(action='files-rest-object-delete-version', role=contributor_role),
            ActionRoles(action='files-rest-object-read', role=contributor_role),
            ActionRoles(action='search-access', role=contributor_role),
            ActionRoles(action='detail-page-acces', role=contributor_role),
            ActionRoles(action='download-original-pdf-access', role=contributor_role),
            ActionRoles(action='author-access', role=contributor_role),
            ActionRoles(action='items-autofill', role=contributor_role),
            ActionRoles(action='detail-page-acces', role=contributor_role),
            ActionRoles(action='detail-page-acces', role=contributor_role),
        ]
        db.session.add_all(action_roles)
        
    return [
        {'email': contributor.email, 'id': contributor.id, 'obj': contributor},
        {'email': repoadmin.email, 'id': repoadmin.id, 'obj': repoadmin},
        {'email': sysadmin.email, 'id': sysadmin.id, 'obj': sysadmin},
        {'email': comadmin.email, 'id': comadmin.id, 'obj': comadmin},
        {'email': generaluser.email, 'id': generaluser.id, 'obj': sysadmin},
        {'email': originalroleuser.email, 'id': originalroleuser.id, 'obj': originalroleuser},
        {'email': originalroleuser2.email, 'id': originalroleuser2.id, 'obj': originalroleuser2},
        {'email': user.email, 'id': user.id, 'obj': user},
    ]

@pytest.fixture()
def db_oaischema(app, db):
    schema_name='jpcoar_mapping'
    form_data={"name": "jpcoar", "file_name": "jpcoar_scm.xsd", "root_name": "jpcoar"}
    xsd = "{\"dc:title\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 1, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"dcterms:alternative\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:creator\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"jpcoar:nameIdentifier\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"nameIdentifierScheme\", \"ref\": null, \"restriction\": {\"enumeration\": [\"e-Rad\", \"NRID\", \"ORCID\", \"ISNI\", \"VIAF\", \"AID\", \"kakenhi\", \"Ringgold\", \"GRID\"]}}, {\"use\": \"optional\", \"name\": \"nameIdentifierURI\", \"ref\": null}]}}, \"jpcoar:creatorName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:familyName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:givenName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:creatorAlternative\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:affiliation\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"jpcoar:nameIdentifier\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"nameIdentifierScheme\", \"ref\": null, \"restriction\": {\"enumeration\": [\"e-Rad\", \"NRID\", \"ORCID\", \"ISNI\", \"VIAF\", \"AID\", \"kakenhi\", \"Ringgold\", \"GRID\"]}}, {\"use\": \"optional\", \"name\": \"nameIdentifierURI\", \"ref\": null}]}}, \"jpcoar:affiliationName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}}}, \"jpcoar:contributor\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"contributorType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"ContactPerson\", \"DataCollector\", \"DataCurator\", \"DataManager\", \"Distributor\", \"Editor\", \"HostingInstitution\", \"Producer\", \"ProjectLeader\", \"ProjectManager\", \"ProjectMember\", \"RegistrationAgency\", \"RegistrationAuthority\", \"RelatedPerson\", \"Researcher\", \"ResearchGroup\", \"Sponsor\", \"Supervisor\", \"WorkPackageLeader\", \"Other\"]}}]}, \"jpcoar:nameIdentifier\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"nameIdentifierScheme\", \"ref\": null, \"restriction\": {\"enumeration\": [\"e-Rad\", \"NRID\", \"ORCID\", \"ISNI\", \"VIAF\", \"AID\", \"kakenhi\", \"Ringgold\", \"GRID\"]}}, {\"use\": \"optional\", \"name\": \"nameIdentifierURI\", \"ref\": null}]}}, \"jpcoar:contributorName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:familyName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:givenName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:contributorAlternative\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:affiliation\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"jpcoar:nameIdentifier\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"nameIdentifierScheme\", \"ref\": null, \"restriction\": {\"enumeration\": [\"e-Rad\", \"NRID\", \"ORCID\", \"ISNI\", \"VIAF\", \"AID\", \"kakenhi\", \"Ringgold\", \"GRID\"]}}, {\"use\": \"optional\", \"name\": \"nameIdentifierURI\", \"ref\": null}]}}, \"jpcoar:affiliationName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}}}, \"dcterms:accessRights\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"rdf:resource\", \"ref\": \"rdf:resource\"}], \"restriction\": {\"enumeration\": [\"embargoed access\", \"metadata only access\", \"open access\", \"restricted access\"]}}}, \"rioxxterms:apc\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"restriction\": {\"enumeration\": [\"Paid\", \"Partially waived\", \"Fully waived\", \"Not charged\", \"Not required\", \"Unknown\"]}}}, \"dc:rights\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"rdf:resource\", \"ref\": \"rdf:resource\"}, {\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:rightsHolder\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"jpcoar:nameIdentifier\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"nameIdentifierScheme\", \"ref\": null, \"restriction\": {\"enumeration\": [\"e-Rad\", \"NRID\", \"ORCID\", \"ISNI\", \"VIAF\", \"AID\", \"kakenhi\", \"Ringgold\", \"GRID\"]}}, {\"use\": \"optional\", \"name\": \"nameIdentifierURI\", \"ref\": null}]}}, \"jpcoar:rightsHolderName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}}, \"jpcoar:subject\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}, {\"use\": \"optional\", \"name\": \"subjectURI\", \"ref\": null}, {\"use\": \"required\", \"name\": \"subjectScheme\", \"ref\": null, \"restriction\": {\"enumeration\": [\"BSH\", \"DDC\", \"LCC\", \"LCSH\", \"MeSH\", \"NDC\", \"NDLC\", \"NDLSH\", \"Sci-Val\", \"UDC\", \"Other\"]}}]}}, \"datacite:description\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}, {\"use\": \"required\", \"name\": \"descriptionType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"Abstract\", \"Methods\", \"TableOfContents\", \"TechnicalInfo\", \"Other\"]}}]}}, \"dc:publisher\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"datacite:date\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"dateType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"Accepted\", \"Available\", \"Collected\", \"Copyrighted\", \"Created\", \"Issued\", \"Submitted\", \"Updated\", \"Valid\"]}}]}}, \"dc:language\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"restriction\": {\"patterns\": [\"^[a-z]{3}$\"]}}}, \"dc:type\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 1, \"attributes\": [{\"use\": \"required\", \"name\": \"rdf:resource\", \"ref\": \"rdf:resource\"}], \"restriction\": {\"enumeration\": [\"conference paper\", \"data paper\", \"departmental bulletin paper\", \"editorial\", \"journal article\", \"newspaper\", \"periodical\", \"review article\", \"software paper\", \"article\", \"book\", \"book part\", \"cartographic material\", \"map\", \"conference object\", \"conference proceedings\", \"conference poster\", \"dataset\", \"aggregated data\", \"clinical trial data\", \"compiled data\", \"encoded data\", \"experimental data\", \"genomic data\", \"geospatial data\", \"laboratory notebook\", \"measurement and test data\", \"observational data\", \"recorded data\", \"simulation data\", \"survey data\", \"interview\", \"image\", \"still image\", \"moving image\", \"video\", \"lecture\", \"patent\", \"internal report\", \"report\", \"research report\", \"technical report\", \"policy report\", \"report part\", \"working paper\", \"data management plan\", \"sound\", \"thesis\", \"bachelor thesis\", \"master thesis\", \"doctoral thesis\", \"interactive resource\", \"learning object\", \"manuscript\", \"musical notation\", \"research proposal\", \"software\", \"technical documentation\", \"workflow\", \"other\"]}}}, \"datacite:version\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"oaire:versiontype\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"rdf:resource\", \"ref\": \"rdf:resource\"}], \"restriction\": {\"enumeration\": [\"AO\", \"SMUR\", \"AM\", \"P\", \"VoR\", \"CVoR\", \"EVoR\", \"NA\"]}}}, \"jpcoar:identifier\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"identifierType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"DOI\", \"HDL\", \"URI\"]}}]}}, \"jpcoar:identifierRegistration\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"identifierType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"JaLC\", \"Crossref\", \"DataCite\", \"PMID\"]}}]}}, \"jpcoar:relation\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"relationType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"isVersionOf\", \"hasVersion\", \"isPartOf\", \"hasPart\", \"isReferencedBy\", \"references\", \"isFormatOf\", \"hasFormat\", \"isReplacedBy\", \"replaces\", \"isRequiredBy\", \"requires\", \"isSupplementTo\", \"isSupplementedBy\", \"isIdenticalTo\", \"isDerivedFrom\", \"isSourceOf\"]}}]}, \"jpcoar:relatedIdentifier\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"identifierType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"ARK\", \"arXiv\", \"DOI\", \"HDL\", \"ICHUSHI\", \"ISBN\", \"J-GLOBAL\", \"Local\", \"PISSN\", \"EISSN\", \"NAID\", \"PMID\", \"PURL\", \"SCOPUS\", \"URI\", \"WOS\"]}}]}}, \"jpcoar:relatedTitle\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}}, \"dcterms:temporal\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"datacite:geoLocation\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"datacite:geoLocationPoint\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}, \"datacite:pointLongitude\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 1, \"restriction\": {\"maxInclusive\": 180, \"minInclusive\": -180}}}, \"datacite:pointLatitude\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 1, \"restriction\": {\"maxInclusive\": 90, \"minInclusive\": -90}}}}, \"datacite:geoLocationBox\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}, \"datacite:westBoundLongitude\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 1, \"restriction\": {\"maxInclusive\": 180, \"minInclusive\": -180}}}, \"datacite:eastBoundLongitude\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 1, \"restriction\": {\"maxInclusive\": 180, \"minInclusive\": -180}}}, \"datacite:southBoundLatitude\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 1, \"restriction\": {\"maxInclusive\": 90, \"minInclusive\": -90}}}, \"datacite:northBoundLatitude\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 1, \"restriction\": {\"maxInclusive\": 90, \"minInclusive\": -90}}}}, \"datacite:geoLocationPlace\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}}}, \"jpcoar:fundingReference\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"datacite:funderIdentifier\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"funderIdentifierType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"Crossref Funder\", \"GRID\", \"ISNI\", \"Other\"]}}]}}, \"jpcoar:funderName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 1, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"datacite:awardNumber\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"awardURI\", \"ref\": null}]}}, \"jpcoar:awardTitle\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}}, \"jpcoar:sourceIdentifier\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"identifierType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"PISSN\", \"EISSN\", \"ISSN\", \"NCID\"]}}]}}, \"jpcoar:sourceTitle\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:volume\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"jpcoar:issue\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"jpcoar:numPages\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"jpcoar:pageStart\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"jpcoar:pageEnd\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"dcndl:dissertationNumber\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"dcndl:degreeName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"dcndl:dateGranted\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"jpcoar:degreeGrantor\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"jpcoar:nameIdentifier\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"nameIdentifierScheme\", \"ref\": null, \"restriction\": {\"enumeration\": [\"e-Rad\", \"NRID\", \"ORCID\", \"ISNI\", \"VIAF\", \"AID\", \"kakenhi\", \"Ringgold\", \"GRID\"]}}, {\"use\": \"optional\", \"name\": \"nameIdentifierURI\", \"ref\": null}]}}, \"jpcoar:degreeGrantorName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}}, \"jpcoar:conference\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"jpcoar:conferenceName\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:conferenceSequence\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"jpcoar:conferenceSponsor\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:conferenceDate\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"startMonth\", \"ref\": null, \"restriction\": {\"maxInclusive\": 12, \"minInclusive\": 1, \"totalDigits\": 2}}, {\"use\": \"optional\", \"name\": \"endYear\", \"ref\": null, \"restriction\": {\"maxInclusive\": 2200, \"minInclusive\": 1400, \"totalDigits\": 4}}, {\"use\": \"optional\", \"name\": \"startDay\", \"ref\": null, \"restriction\": {\"maxInclusive\": 31, \"minInclusive\": 1, \"totalDigits\": 2}}, {\"use\": \"optional\", \"name\": \"endDay\", \"ref\": null, \"restriction\": {\"maxInclusive\": 31, \"minInclusive\": 1, \"totalDigits\": 2}}, {\"use\": \"optional\", \"name\": \"endMonth\", \"ref\": null, \"restriction\": {\"maxInclusive\": 12, \"minInclusive\": 1, \"totalDigits\": 2}}, {\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}, {\"use\": \"optional\", \"name\": \"startYear\", \"ref\": null, \"restriction\": {\"maxInclusive\": 2200, \"minInclusive\": 1400, \"totalDigits\": 4}}]}}, \"jpcoar:conferenceVenue\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:conferencePlace\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"xml:lang\", \"ref\": \"xml:lang\"}]}}, \"jpcoar:conferenceCountry\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"restriction\": {\"patterns\": [\"^[A-Z]{3}$\"]}}}}, \"jpcoar:file\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}, \"jpcoar:URI\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0, \"attributes\": [{\"use\": \"optional\", \"name\": \"label\", \"ref\": null}, {\"use\": \"optional\", \"name\": \"objectType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"abstract\", \"dataset\", \"fulltext\", \"software\", \"summary\", \"thumbnail\", \"other\"]}}]}}, \"jpcoar:mimeType\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}, \"jpcoar:extent\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0}}, \"datacite:date\": {\"type\": {\"maxOccurs\": \"unbounded\", \"minOccurs\": 0, \"attributes\": [{\"use\": \"required\", \"name\": \"dateType\", \"ref\": null, \"restriction\": {\"enumeration\": [\"Accepted\", \"Available\", \"Collected\", \"Copyrighted\", \"Created\", \"Issued\", \"Submitted\", \"Updated\", \"Valid\"]}}]}}, \"datacite:version\": {\"type\": {\"maxOccurs\": 1, \"minOccurs\": 0}}}, \"custom:system_file\": {\"type\": {\"minOccurs\": 0, \"maxOccurs\": \"unbounded\"}, \"jpcoar:URI\": {\"type\": {\"minOccurs\": 0, \"maxOccurs\": 1, \"attributes\": [{\"name\": \"objectType\", \"ref\": null, \"use\": \"optional\", \"restriction\": {\"enumeration\": [\"abstract\", \"summary\", \"fulltext\", \"thumbnail\", \"other\"]}}, {\"name\": \"label\", \"ref\": null, \"use\": \"optional\"}]}}, \"jpcoar:mimeType\": {\"type\": {\"minOccurs\": 0, \"maxOccurs\": 1}}, \"jpcoar:extent\": {\"type\": {\"minOccurs\": 0, \"maxOccurs\": \"unbounded\"}}, \"datacite:date\": {\"type\": {\"minOccurs\": 1, \"maxOccurs\": \"unbounded\", \"attributes\": [{\"name\": \"dateType\", \"ref\": null, \"use\": \"required\", \"restriction\": {\"enumeration\": [\"Accepted\", \"Available\", \"Collected\", \"Copyrighted\", \"Created\", \"Issued\", \"Submitted\", \"Updated\", \"Valid\"]}}]}}, \"datacite:version\": {\"type\": {\"minOccurs\": 0, \"maxOccurs\": 1}}}}"
    namespaces={"": "https://github.com/JPCOAR/schema/blob/master/1.0/", "dc": "http://purl.org/dc/elements/1.1/", "xs": "http://www.w3.org/2001/XMLSchema", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "xml": "http://www.w3.org/XML/1998/namespace", "dcndl": "http://ndl.go.jp/dcndl/terms/", "oaire": "http://namespace.openaire.eu/schema/oaire/", "jpcoar": "https://github.com/JPCOAR/schema/blob/master/1.0/", "dcterms": "http://purl.org/dc/terms/", "datacite": "https://schema.datacite.org/meta/kernel-4/", "rioxxterms": "http://www.rioxx.net/schema/v2.0/rioxxterms/"}
    schema_location='https://github.com/JPCOAR/schema/blob/master/1.0/jpcoar_scm.xsd'
    oaischema = OAIServerSchema(id=uuid.uuid4(),schema_name=schema_name,form_data=form_data,xsd=xsd,namespaces=namespaces,schema_location=schema_location,isvalid=True,is_mapping=False,isfixed=False,version_id=1)
    with db.session.begin_nested():
        db.session.add(oaischema)

@pytest.fixture()
def db_userprofile(app, db):
    profiles = {}
    with db.session.begin_nested():
        users = User.query.all()
        for user in users:
            p = UserProfile()
            p.user_id  = user.id
            p._username = (user.email).split('@')[0]
            profiles[user.email] = p
            db.session.add(p)
    return profiles
        
        


@pytest.fixture()
def db_register(app, db):
    item_type_name = ItemTypeName(name='テストアイテムタイプ',
                                  has_site_license=True,
                                  is_active=True)
    item_type_schema=dict()
    with open('tests/data/itemtype_schema.json', 'r') as f:
        item_type_schema = json.load(f)
    
    item_type_form=dict()
    with open('tests/data/itemtype_form.json', 'r') as f:
        item_type_form = json.load(f)
    
    item_type_render=dict()
    with open('tests/data/itemtype_render.json', 'r') as f:
        item_type_render = json.load(f)
    
    item_type_mapping=dict()
    with open('tests/data/itemtype_mapping.json', 'r') as f:
        item_type_mapping = json.load(f)

    item_type = ItemType(name_id=1,harvesting_type=True,
                         schema=item_type_schema,
                         form=item_type_form,
                         render=item_type_render,
                         tag=1,version_id=1,is_deleted=False)
    
    item_type_mapping = ItemTypeMapping(item_type_id=1,mapping=item_type_mapping)

    with db.session.begin_nested():
        db.session.add(item_type_name)
        db.session.add(item_type)
        db.session.add(item_type_mapping)
        
    return {'item_type_name':item_type_name,'item_type':item_type}

@pytest.fixture()
def db_records(db,instance_path):
    with db.session.begin_nested():
        Location.query.delete()
        loc = Location(name='local', uri=instance_path, default=True)
        db.session.add(loc)
    db.session.commit()

    record_data = json_data("data/test_records.json")
    item_data = json_data("data/test_items.json")
    record_num = len(record_data)
    result = []
    for d in range(record_num):
        result.append(create_record(record_data[d], item_data[d]))
    db.session.commit()

    yield result

@pytest.fixture()
def db_register2(app, db,db_register,users):
    action_datas=dict()
    with open('tests/data/actions.json', 'r') as f:
        action_datas = json.load(f)
    actions_db = list()
    with db.session.begin_nested():
        for data in action_datas:
            actions_db.append(Action(**data))
        db.session.add_all(actions_db)
    
    actionstatus_datas = dict()
    with open('tests/data/action_status.json') as f:
        actionstatus_datas = json.load(f)
    actionstatus_db = list()
    with db.session.begin_nested():
        for data in actionstatus_datas:
            actionstatus_db.append(ActionStatus(**data))
        db.session.add_all(actionstatus_db)
    
    flow_id = uuid.uuid4()
    flow_define = FlowDefine(flow_id=flow_id,flow_name='Registration Flow',flow_user=1,flow_status="A")
    flow_action1 = FlowAction(status='N',
                     flow_id=flow_id,
                     action_id=1,
                     action_version='1.0.0',
                     action_order=1,
                     action_condition='',
                     action_status='A',
                     action_date=datetime.strptime('2018/07/28 0:00:00','%Y/%m/%d %H:%M:%S'),
                     send_mail_setting={})
    flow_action2 = FlowAction(status='N',
                     flow_id=flow_id,
                     action_id=3,
                     action_version='1.0.0',
                     action_order=2,
                     action_condition='',
                     action_status='A',
                     action_date=datetime.strptime('2018/07/28 0:00:00','%Y/%m/%d %H:%M:%S'),
                     send_mail_setting={})
    flow_action3 = FlowAction(status='N',
                     flow_id=flow_id,
                     action_id=5,
                     action_version='1.0.0',
                     action_order=3,
                     action_condition='',
                     action_status='A',
                     action_date=datetime.strptime('2018/07/28 0:00:00','%Y/%m/%d %H:%M:%S'),
                     send_mail_setting={})
    
    workflow = WorkFlow(flows_id=uuid.uuid4(),
                        flows_name='test workflow1',
                        itemtype_id=1,
                        index_tree_id=None,
                        flow_id=1,
                        is_deleted=False,
                        open_restricted=False,
                        location_id=None,
                        is_gakuninrdm=False)
    activity = Activity(activity_id='A-00000000-00000',workflow_id=1, flow_id=flow_define.id,
                    action_id=1, activity_login_user=1,
                    activity_update_user=1,
                    activity_start=datetime.strptime('2022/04/14 3:01:53.931', '%Y/%m/%d %H:%M:%S.%f'),
                    activity_community_id=3,
                    activity_confirm_term_of_use=True,
                    title='test', shared_user_id=-1, extra_info={},
                    action_order=6)

    with db.session.begin_nested():
        db.session.add(flow_define)
        db.session.add(flow_action1)
        db.session.add(flow_action2)
        db.session.add(flow_action3)
        db.session.add(workflow)
        db.session.add(activity)

    return {'flow_define':flow_define}


@pytest.fixture()
def db_sessionlifetime(app, db):
    session_lifetime = SessionLifetime(lifetime=60,is_delete=False)
    with db.session.begin_nested():
        db.session.add(session_lifetime)