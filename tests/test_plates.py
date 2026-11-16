"""One vehicle per plate (however it is typed); a repeated phone number only warns."""
import pytest
from sqlalchemy.exc import IntegrityError

from harithmapos import db
from harithmapos.models import Customer, Employee, Vehicle, WashBay
from harithmapos.textutils import plate_key


@pytest.fixture
def car(app):
    with app.app_context():
        owner = Customer.query.filter_by(name='Kamal Perera').one()
        db.session.add(Vehicle(number='CAB-1234', owner_id=owner.id))
        db.session.commit()
        return owner.id


def test_plate_keys():
    assert plate_key('CAB-1234') == plate_key('cab 1234') == plate_key(' CAB1234') == 'CAB1234'
    assert plate_key('65-1234') == '651234' and plate_key('--') is None


def test_the_database_refuses_a_second_vehicle_with_the_same_plate(app, car):
    with app.app_context():
        db.session.add(Vehicle(number='CAB 1234', owner_id=car))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_adding_the_same_plate_on_the_customer_page_is_refused(app, owner, car):
    with app.app_context():
        other = Customer(name='Saman Fernando', contact='712345678')
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    page = owner.post('/app/insert_vehicle/', data={'number': 'cab1234', 'owner_id': other_id},
                      follow_redirects=True).get_data(as_text=True)
    assert 'CAB-1234 is already registered to Kamal Perera' in page
    with app.app_context():
        assert Vehicle.query.count() == 1


def test_renaming_a_plate_to_one_already_used_is_refused(app, owner, car):
    with app.app_context():
        v = Vehicle(number='CAD-5555', owner_id=car)
        db.session.add(v)
        db.session.commit()
        vid = v.id
    page = owner.post(f'/app/vehicle/{vid}/update', data={'number': 'CAB 1234', 'owner_id': car},
                      follow_redirects=True).get_data(as_text=True)
    assert 'already registered to Kamal Perera' in page
    with app.app_context():
        assert db.session.get(Vehicle, vid).number == 'CAD-5555'


def test_quick_register_finds_the_vehicle_however_it_is_typed(app, owner, car):
    page = owner.post('/app/customer/quick', data={'name': 'Someone Else', 'contact': '0712345678', 'number': 'cab 1234'},
                      follow_redirects=True).get_data(as_text=True)
    assert 'already registered to Kamal Perera' in page
    with app.app_context():
        assert Vehicle.query.count() == 1 and Customer.query.filter_by(name='Someone Else').count() == 0


def test_the_floor_board_uses_the_registered_vehicle(app, owner, car):
    with app.app_context():
        e, b = Employee(name='Nimal'), WashBay(name='Bay 1')
        db.session.add_all([e, b])
        db.session.commit()
        e_id, b_id = e.id, b.id
    owner.post('/app/floor/add', data={'number': 'cab1234', 'employee_id': e_id, 'washbay_id': b_id})
    with app.app_context():
        from harithmapos.models import InvoiceHead
        assert Vehicle.query.count() == 1
        assert [i.vehicle.number for i in InvoiceHead.query.all()] == ['CAB-1234']


def test_vehicle_search_ignores_dashes(app, owner, car):
    assert [v['number'] for v in owner.get('/app/search/vehicles?q=cab1234').get_json()] == ['CAB-1234']


def test_a_repeated_phone_number_only_warns(app, owner):
    page = owner.post('/app/insert_customer/', data={'name': 'Nadeesha Perera', 'contact': '077 123 4567'},
                      follow_redirects=True).get_data(as_text=True)
    assert 'Nadeesha Perera added' in page and 'is also the phone number of Kamal Perera' in page
    with app.app_context():
        assert Customer.query.filter(Customer.contact.in_(['771234567', '0771234567'])).count() == 2


def test_a_new_phone_number_says_nothing(app, owner):
    page = owner.post('/app/insert_customer/', data={'name': 'Ruwan Silva', 'contact': '0759876543'},
                      follow_redirects=True).get_data(as_text=True)
    assert 'Ruwan Silva added' in page and 'also the phone number' not in page
