const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const API = window.location.origin;
let balance = 500;
let inventory = [];

const auth = tg.initData || "";

async function request(url, method = "GET", body = null) {
    const options = {
        method,
        headers: {
            "Content-Type": "application/json",
            "Authorization": auth
        }
    };

    if (body) options.body = JSON.stringify(body);

    const response = await fetch(API + url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Ошибка");
    }

    return data;
}

async function loadUser() {
    try {
        const user = await request("/api/me");
        balance = user.balance;
        inventory = user.inventory || [];
        updateBalance();
    } catch (error) {
        console.log(error.message);
    }
}

function updateBalance() {
    document.getElementById("balance").textContent = balance;
}

function showPage(page) {
    const content = document.getElementById("content");

    if (page === "home") {
        content.innerHTML = `
            <h2>💎 Добро пожаловать!</h2>
            <p>Добро пожаловать в мир GemUp!</p>
            <p>Открывай кейсы, собирай предметы и пополняй свою коллекцию.</p>
            <button class="main-button" onclick="showPage('cases')">
                ОТКРЫТЬ КЕЙСЫ
            </button>
            <button class="main-button" onclick="dailyBonus()">
                🎁 ЕЖЕДНЕВНЫЙ БОНУС
            </button>
        `;
    }

    if (page === "cases") {
        content.innerHTML = `
            <h2>🎁 КЕЙСЫ GEMUP</h2>
            <div class="case">
                <h3>🔴 Basic Case</h3>
                <p>Стоимость: 100 💎</p>
                <button class="main-button" onclick="openCase('basic')">ОТКРЫТЬ</button>
            </div>
            <div class="case">
                <h3>🟣 Rare Case</h3>
                <p>Стоимость: 500 💎</p>
                <button class="main-button" onclick="openCase('rare')">ОТКРЫТЬ</button>
            </div>
            <div class="case">
                <h3>👑 Legend Case</h3>
                <p>Стоимость: 1500 💎</p>
                <button class="main-button" onclick="openCase('legend')">ОТКРЫТЬ</button>
            </div>
        `;
    }

    if (page === "inventory") {
        content.innerHTML = `
            <h2>🎒 МОЙ ИНВЕНТАРЬ</h2>
            <div id="items">Загрузка...</div>
        `;
        loadInventory();
    }

    if (page === "profile") {
        content.innerHTML = `
            <h2>👤 ПРОФИЛЬ</h2>
            <p>Игрок: ${tg.initDataUnsafe?.user?.username || "Player"}</p>
            <p>Баланс: 💎 ${balance}</p>
            <button class="main-button" onclick="dailyBonus()">ПОЛУЧИТЬ БОНУС</button>
        `;
    }
}

async function openCase(type) {
    try {
        const result = await request("/api/case/open", "POST", {
            case: type
        });

        balance -= ({
            basic: 100,
            rare: 500,
            legend: 1500
        })[type];

        updateBalance();

        tg.showPopup({
            title: "💎 GEMUP",
            message: `Поздравляем! Твой выигрыш: ${result.reward} 💎`,
            buttons: [{type: "ok"}]
        });

        await loadUser();

    } catch (error) {
        alert(error.message);
    }
}

async function dailyBonus() {
    try {
        const result = await request("/api/daily", "POST");
        alert(`🎁 Ты получил ${result.reward} 💎`);
        await loadUser();
    } catch (error) {
        alert(error.message);
    }
}

async function loadInventory() {
    try {
        inventory = await request("/api/inventory");

        const items = document.getElementById("items");

        if (!inventory.length) {
            items.innerHTML = "<p>Инвентарь пока пуст.</p>";
            return;
        }

        items.innerHTML = inventory.map(item => `
            <div class="case">
                <h3>💎 ${item.name}</h3>
                <p>Стоимость: ${item.value} монет</p>
            </div>
        `).join("");

    } catch (error) {
        document.getElementById("items").innerHTML = error.message;
    }
}

loadUser();
