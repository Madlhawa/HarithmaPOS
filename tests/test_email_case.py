"""Sign-in emails ignore case and surrounding spaces."""
import pytest
from sqlalchemy.exc import IntegrityError

from harithmapos import db
from harithmapos.models import User
from harithmapos.textutils import normalize_email
from conftest import PASSWORD


def test_normalize_email():
    assert normalize_email('  Owner@Example.COM ') == 'owner@example.com'
    assert normalize_email('') is None and normalize_email(None) is None


@pytest.mark.parametrize('typed', ['OWNER@example.com', ' Owner@Example.com '])
def test_sign_in_ignores_case_and_spaces(app, typed):
    r = app.test_client().post('/app/login', data={'email': typed, 'password': PASSWORD})
    assert r.status_code == 302 and '/app/login' not in r.headers['Location']


def test_model_stores_lower_case(app):
    with app.app_context():
        user = User(name='Mixed Case', email='Mixed.Case@Example.com', password='x')
        db.session.add(user)
        db.session.commit()
        assert user.email == 'mixed.case@example.com'


def test_database_refuses_capitals(app):
    with app.app_context():
        with pytest.raises(IntegrityError):
            db.session.execute(db.text(
                "INSERT INTO \"user\" (email, name, password, role, active, create_dttm, update_dttm) "
                "VALUES ('Caps@Example.com', 'Caps', 'x', 'staff', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        db.session.rollback()


def test_cannot_add_a_second_account_for_the_same_mailbox(app, owner):
    r = owner.post('/app/register', data={'name': 'Copy', 'email': 'STAFF@example.com', 'password': PASSWORD,
                                           'confirm_password': PASSWORD, 'role': 'staff'})
    assert 'already exists' in r.get_data(as_text=True)
    with app.app_context():
        assert User.query.count() == 2


def test_new_user_is_saved_in_lower_case(app, owner):
    owner.post('/app/register', data={'name': 'Nimal', 'email': ' Nimal@Example.com', 'password': PASSWORD,
                                      'confirm_password': PASSWORD, 'role': 'staff'})
    with app.app_context():
        assert User.query.filter_by(email='nimal@example.com').count() == 1


def test_editing_a_user_cannot_take_another_users_email(app, owner):
    with app.app_context():
        staff_id = User.query.filter_by(email='staff@example.com').one().id
    r = owner.post(f'/app/users/{staff_id}', data={'name': 'Sam Staff', 'email': 'Owner@Example.com',
                                                   'role': 'staff', 'active': 'y'})
    assert 'Another user already has this email' in r.get_data(as_text=True)


def test_password_reset_finds_the_account_whatever_the_case(app, monkeypatch):
    sent = []
    monkeypatch.setattr('harithmapos.views.user.routes.send_reset_email', lambda user: sent.append(user.email))
    app.test_client().post('/app/reset_password', data={'email': 'Staff@EXAMPLE.com'})
    assert sent == ['staff@example.com']


def test_create_user_command_lower_cases(app):
    result = app.test_cli_runner().invoke(args=['create-user', '--name', 'Cli', '--email', 'CLI@Example.com',
                                                '--password', PASSWORD])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert User.query.filter_by(email='cli@example.com').count() == 1
