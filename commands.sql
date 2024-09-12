CREATE TABLE userprofile (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT DEFAULT NULL,
    username VARCHAR(256) DEFAULT NULL,
    name VARCHAR(255) DEFAULT NULL
);

CREATE TABLE backend_hall (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) DEFAULT NULL,
    size VARCHAR(255) NOT NULL,
    img VARCHAR(255) DEFAULT NULL
);

CREATE TABLE backend_order_hall (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `hall_id` INT NOT NULL,
    `contact` VARCHAR(256)
);

CREATE TABLE backend_basket (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `products_id` INT NOT NULL,
    `amount` INT
);

CREATE TABLE `backend_about_us` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `image_products` VARCHAR(255) DEFAULT NULL,
    `text` TEXT DEFAULT NULL
);

CREATE TABLE `backend_contacts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `text` TEXT DEFAULT NULL
);
