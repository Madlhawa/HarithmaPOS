-- Sample Items Insert Script for HarithmaPOS
-- This script inserts multiple items to test pagination functionality
-- Prices are in LKR (Sri Lankan Rupees)
-- Uses predefined UOMs for consistency

-- Car Wash Products
INSERT INTO item (name, description, unit_of_measure, quantity, unit_cost, unit_price, discount_pct, create_dttm, update_dttm) VALUES
('Car Shampoo', 'Premium car wash shampoo for exterior cleaning', 'Piece', 50.0000, 15.50, 25.00, 0.00, NOW(), NOW()),
('Tire Cleaner', 'Heavy-duty tire and rim cleaner', 'Piece', 30.0000, 12.75, 20.00, 5.00, NOW(), NOW()),
('Wax Polish', 'High-quality carnauba wax for shine and protection', 'Kilogram', 25.0000, 35.00, 55.00, 0.00, NOW(), NOW()),
('Glass Cleaner', 'Ammonia-free glass cleaner for windows and mirrors', 'Piece', 40.0000, 8.50, 15.00, 0.00, NOW(), NOW()),
('Dashboard Polish', 'Interior dashboard cleaner and protectant', 'Piece', 35.0000, 18.25, 30.00, 10.00, NOW(), NOW()),

-- Cleaning Supplies
('Microfiber Towels', 'Premium microfiber cleaning towels (pack of 5)', 'Piece', 20.0000, 25.00, 40.00, 0.00, NOW(), NOW()),
('Sponges', 'Soft car wash sponges for gentle cleaning', 'Piece', 100.0000, 3.50, 6.00, 0.00, NOW(), NOW()),
('Scrub Brushes', 'Heavy-duty scrub brushes for wheels and tires', 'Piece', 15.0000, 12.00, 20.00, 0.00, NOW(), NOW()),
('Buckets', 'Large plastic buckets for water and soap', 'Piece', 10.0000, 15.00, 25.00, 0.00, NOW(), NOW()),
('Pressure Washer Soap', 'Concentrated soap for pressure washer systems', 'Liter', 8.0000, 45.00, 75.00, 0.00, NOW(), NOW()),

-- Interior Care Products
('Leather Conditioner', 'Premium leather conditioner for seats and upholstery', 'Piece', 12.0000, 28.75, 45.00, 0.00, NOW(), NOW()),
('Fabric Cleaner', 'Multi-purpose fabric cleaner for car interiors', 'Piece', 18.0000, 16.50, 28.00, 5.00, NOW(), NOW()),
('Air Freshener', 'Long-lasting car air freshener (vanilla scent)', 'Piece', 50.0000, 4.25, 8.00, 0.00, NOW(), NOW()),
('Vacuum Bags', 'Replacement bags for shop vacuum cleaners', 'Piece', 25.0000, 12.00, 20.00, 0.00, NOW(), NOW()),
('Steam Cleaner Solution', 'Specialized solution for steam cleaning upholstery', 'Piece', 14.0000, 22.50, 38.00, 0.00, NOW(), NOW()),

-- Protective Products
('Paint Sealant', 'Advanced paint protection sealant', 'Piece', 8.0000, 65.00, 95.00, 0.00, NOW(), NOW()),
('Ceramic Coating', 'Professional-grade ceramic coating kit', 'Piece', 5.0000, 125.00, 200.00, 15.00, NOW(), NOW()),
('Paint Protection Film', 'Clear protective film for paint (per foot)', 'Square Meter', 200.0000, 8.75, 15.00, 0.00, NOW(), NOW()),
('Rust Inhibitor', 'Underbody rust protection spray', 'Piece', 22.0000, 18.50, 32.00, 0.00, NOW(), NOW()),
('UV Protection Spray', 'UV protection for interior surfaces', 'Piece', 16.0000, 24.00, 42.00, 0.00, NOW(), NOW()),

-- Tools and Equipment
('Foam Cannon', 'High-pressure foam cannon for car wash systems', 'Piece', 3.0000, 85.00, 140.00, 0.00, NOW(), NOW()),
('Clay Bar Kit', 'Complete clay bar detailing kit', 'Piece', 6.0000, 45.00, 75.00, 0.00, NOW(), NOW()),
('Polishing Pads', 'Professional polishing pads for buffer', 'Piece', 10.0000, 35.00, 60.00, 0.00, NOW(), NOW()),
('Drying Blower', 'High-speed car drying blower', 'Piece', 2.0000, 150.00, 250.00, 10.00, NOW(), NOW()),
('Water Spot Remover', 'Professional water spot and mineral deposit remover', 'Piece', 20.0000, 19.75, 35.00, 0.00, NOW(), NOW()),

-- Maintenance Supplies
('Oil Filter', 'High-quality engine oil filter', 'Piece', 30.0000, 12.50, 20.00, 0.00, NOW(), NOW()),
('Air Filter', 'Engine air filter replacement', 'Piece', 25.0000, 15.00, 25.00, 0.00, NOW(), NOW()),
('Brake Fluid', 'DOT 3 brake fluid', 'Liter', 15.0000, 8.75, 15.00, 0.00, NOW(), NOW()),
('Coolant', 'Antifreeze/coolant (pre-mixed)', 'Liter', 12.0000, 18.50, 30.00, 0.00, NOW(), NOW()),
('Transmission Fluid', 'Automatic transmission fluid', 'Liter', 20.0000, 22.00, 35.00, 5.00, NOW(), NOW()),

-- Specialty Products
('Bug Remover', 'Heavy-duty bug and tar remover', 'Piece', 28.0000, 14.25, 24.00, 0.00, NOW(), NOW()),
('Tree Sap Remover', 'Professional tree sap and resin remover', 'Piece', 15.0000, 21.50, 38.00, 0.00, NOW(), NOW()),
('Iron Remover', 'Iron and fallout remover for paint decontamination', 'Piece', 10.0000, 32.00, 55.00, 0.00, NOW(), NOW()),
('Plastic Restorer', 'Black plastic trim restorer and protectant', 'Piece', 18.0000, 16.75, 28.00, 0.00, NOW(), NOW()),
('Chrome Polish', 'Professional chrome and metal polish', 'Piece', 12.0000, 13.50, 22.00, 0.00, NOW(), NOW()),

-- Additional Items for Pagination Testing
('Wheel Cleaner', 'Acid-free wheel cleaner for all wheel types', 'Piece', 24.0000, 11.25, 19.00, 0.00, NOW(), NOW()),
('Trim Restorer', 'UV-resistant trim and bumper restorer', 'Piece', 16.0000, 19.50, 32.00, 0.00, NOW(), NOW()),
('Headlight Cleaner', 'Professional headlight restoration kit', 'Piece', 8.0000, 42.00, 70.00, 0.00, NOW(), NOW()),
('Vinyl Wrap', 'Color-changing vinyl wrap (per yard)', 'Square Meter', 50.0000, 25.00, 45.00, 0.00, NOW(), NOW()),
('Detailing Clay', 'Professional detailing clay bars', 'Piece', 35.0000, 8.75, 15.00, 0.00, NOW(), NOW()),
('Paint Thinner', 'High-quality paint thinner for cleanup', 'Liter', 20.0000, 6.50, 12.00, 0.00, NOW(), NOW()),
('Masking Tape', 'Professional automotive masking tape', 'Piece', 40.0000, 4.25, 8.00, 0.00, NOW(), NOW()),
('Sandpaper', 'Various grit sandpaper for paint prep (pack of 10)', 'Piece', 25.0000, 12.00, 20.00, 0.00, NOW(), NOW()),
('Primer', 'Automotive primer for paint preparation', 'Liter', 15.0000, 18.75, 32.00, 0.00, NOW(), NOW()),
('Clear Coat', 'Professional clear coat finish', 'Liter', 12.0000, 28.50, 48.00, 0.00, NOW(), NOW()),
('Buffing Compound', 'Professional buffing and polishing compound', 'Kilogram', 20.0000, 24.00, 40.00, 0.00, NOW(), NOW()),
('Cutting Compound', 'Heavy-duty cutting compound for paint correction', 'Kilogram', 18.0000, 26.75, 45.00, 0.00, NOW(), NOW()),
('Finishing Polish', 'Ultra-fine finishing polish for show car finish', 'Kilogram', 22.0000, 22.50, 38.00, 0.00, NOW(), NOW()),
('Paint Correction Kit', 'Complete paint correction and polishing kit', 'Piece', 6.0000, 85.00, 140.00, 0.00, NOW(), NOW()),
('Interior Detail Kit', 'Complete interior detailing kit with all products', 'Piece', 8.0000, 65.00, 110.00, 0.00, NOW(), NOW()),
('Exterior Detail Kit', 'Complete exterior detailing kit with all products', 'Piece', 10.0000, 75.00, 125.00, 0.00, NOW(), NOW()),
('Premium Care Kit', 'Premium car care kit with ceramic coating', 'Piece', 4.0000, 150.00, 250.00, 0.00, NOW(), NOW()),
('Basic Wash Kit', 'Basic car wash kit for DIY customers', 'Piece', 15.0000, 35.00, 60.00, 0.00, NOW(), NOW()),
('Professional Kit', 'Professional detailer kit with premium products', 'Piece', 5.0000, 200.00, 350.00, 0.00, NOW(), NOW()),
('Show Car Kit', 'Ultimate show car preparation kit', 'Piece', 3.0000, 300.00, 500.00, 0.00, NOW(), NOW());

-- Display count of inserted items
SELECT 'Total items inserted: ' || COUNT(*) as result FROM item;
