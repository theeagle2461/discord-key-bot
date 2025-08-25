#!/usr/bin/env node
/**
 * Complete Discord Bot with Auto-Reply and Admin Commands
 * A single-file implementation for easy deployment
 */
import { ChannelType, Client, GatewayIntentBits, PermissionFlagsBits, } from 'discord.js';
import express from 'express';
import { createServer } from 'http';
// In-Memory Storage Class
class MemoryStorage {
    botConfig = null;
    autoMessages = new Map();
    discordServers = new Map();
    commandLogs = [];
    botStats;
    constructor() {
        this.botStats = {
            id: this.generateId(),
            totalMessagesSent: '0',
            activeServers: '0',
            autoReplyRate: '0',
            commandsUsed: '0',
            lastUpdated: new Date(),
        };
    }
    generateId() {
        return (Math.random().toString(36).slice(2, 11) + '-' + Date.now().toString(36));
    }
    // Bot Config Methods
    async getBotConfig() {
        return this.botConfig;
    }
    async createBotConfig(data) {
        this.botConfig = {
            id: this.generateId(),
            ...data,
            createdAt: new Date(),
        };
        return this.botConfig;
    }
    async updateBotConfig(id, data) {
        if (this.botConfig && this.botConfig.id === id) {
            this.botConfig = { ...this.botConfig, ...data };
            return this.botConfig;
        }
        return null;
    }
    // Auto Messages Methods
    async getAutoMessages() {
        return Array.from(this.autoMessages.values());
    }
    async getAutoMessagesByType(type) {
        return Array.from(this.autoMessages.values()).filter((msg) => msg.messageType === type);
    }
    async createAutoMessage(data) {
        const message = {
            id: this.generateId(),
            ...data,
            createdAt: new Date(),
        };
        this.autoMessages.set(message.id, message);
        return message;
    }
    async updateAutoMessage(id, data) {
        const existing = this.autoMessages.get(id);
        if (existing) {
            const updated = { ...existing, ...data };
            this.autoMessages.set(id, updated);
            return updated;
        }
        return null;
    }
    async deleteAutoMessage(id) {
        return this.autoMessages.delete(id);
    }
    // Discord Servers Methods
    async getDiscordServers() {
        return Array.from(this.discordServers.values());
    }
    async getDiscordServer(id) {
        return this.discordServers.get(id) || null;
    }
    async createDiscordServer(data) {
        const server = {
            ...data,
            joinedAt: new Date(),
        };
        this.discordServers.set(server.id, server);
        return server;
    }
    async updateDiscordServer(id, data) {
        const existing = this.discordServers.get(id);
        if (existing) {
            const updated = { ...existing, ...data };
            this.discordServers.set(id, updated);
            return updated;
        }
        return null;
    }
    // Command Logs Methods
    async getCommandLogs(limit = 50) {
        return this.commandLogs.slice(-limit).reverse();
    }
    async createCommandLog(data) {
        const log = {
            id: this.generateId(),
            ...data,
            executedAt: new Date(),
        };
        this.commandLogs.push(log);
        // Keep only last 1000 logs
        if (this.commandLogs.length > 1000) {
            this.commandLogs = this.commandLogs.slice(-1000);
        }
        return log;
    }
    // Bot Stats Methods
    async getBotStats() {
        return this.botStats;
    }
    async updateBotStats(data) {
        this.botStats = {
            ...this.botStats,
            ...data,
            lastUpdated: new Date(),
        };
        return this.botStats;
    }
}
// Discord Bot Class
class DiscordBot {
    client;
    isReady = false;
    storage;
    constructor(storage) {
        this.storage = storage;
        this.client = new Client({
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.MessageContent,
                GatewayIntentBits.DirectMessages,
                GatewayIntentBits.DirectMessageReactions,
            ],
        });
        this.setupEventHandlers();
    }
    setupEventHandlers() {
        this.client.once('ready', async () => {
            console.log(`Discord bot ready! Logged in as ${this.client.user?.tag}`);
            this.isReady = true;
            await this.syncServers();
            await this.updateStats();
        });
        this.client.on('messageCreate', async (message) => {
            if (message.author?.bot)
                return;
            // Handle DMs
            if (message.channel?.type === ChannelType.DM) {
                await this.handleDirectMessage(message);
            }
            // Handle commands
            if (message.content?.startsWith('!')) {
                await this.handleCommand(message);
            }
        });
        this.client.on('guildCreate', async (guild) => {
            console.log(`Bot joined guild: ${guild.name}`);
            await this.addServer(guild);
            await this.updateStats();
        });
        this.client.on('guildDelete', async (guild) => {
            console.log(`Bot left guild: ${guild.name}`);
            await this.storage.updateDiscordServer(guild.id, { isActive: false });
            await this.updateStats();
        });
    }
    async start() {
        try {
            const config = await this.storage.getBotConfig();
            if (!config || !config.token) {
                console.error('No bot token found in configuration');
                return;
            }
            await this.client.login(config.token);
        }
        catch (error) {
            console.error('Failed to start Discord bot:', error);
        }
    }
    async stop() {
        if (this.client) {
            await this.client.destroy();
            this.isReady = false;
        }
    }
    async handleDirectMessage(message) {
        try {
            const dmReplies = await this.storage.getAutoMessagesByType('dm_reply');
            for (const autoMessage of dmReplies) {
                if (!autoMessage.isEnabled)
                    continue;
                let shouldReply = false;
                switch (autoMessage.triggerCondition) {
                    case 'any_dm':
                        shouldReply = true;
                        break;
                    case 'keywords':
                        if (autoMessage.keywords && Array.isArray(autoMessage.keywords)) {
                            const messageContent = (message.content || '').toLowerCase();
                            shouldReply = autoMessage.keywords.some((keyword) => messageContent.includes(keyword.toLowerCase()));
                        }
                        break;
                    case 'first_message':
                        shouldReply = true;
                        break;
                }
                if (shouldReply) {
                    await message.reply(autoMessage.content);
                    await this.incrementMessagesSent();
                    break;
                }
            }
        }
        catch (error) {
            console.error('Error handling DM:', error);
        }
    }
    async handleCommand(message) {
        const args = message.content.slice(1).trim().split(/ +/);
        const command = args.shift()?.toLowerCase();
        if (!command)
            return;
        await this.storage.createCommandLog({
            command: `!${command}`,
            userId: message.author.id,
            serverId: message.guild?.id,
            channelId: message.channel.id,
            success: true,
        });
        try {
            switch (command) {
                case 'announce':
                    await this.handleAnnounceCommand(message, args);
                    break;
                case 'say':
                    await this.handleSayCommand(message, args);
                    break;
                case 'config':
                    await this.handleConfigCommand(message);
                    break;
                default:
                    await message.reply('Unknown command. Available commands: !announce, !say, !config');
            }
            await this.incrementCommandsUsed();
        }
        catch (error) {
            console.error(`Error executing command ${command}:`, error);
            await message.reply('An error occurred while executing the command.');
            await this.storage.createCommandLog({
                command: `!${command}`,
                userId: message.author.id,
                serverId: message.guild?.id,
                channelId: message.channel.id,
                success: false,
                errorMessage: error instanceof Error ? error.message : 'Unknown error',
            });
        }
    }
    async handleAnnounceCommand(message, args) {
        const hasPerm = message.member?.permissions.has(PermissionFlagsBits.Administrator);
        if (!hasPerm) {
            await message.reply('You need Administrator permissions to use this command.');
            return;
        }
        if (args.length === 0) {
            await message.reply('Please provide a message to announce. Usage: `!announce <message>`');
            return;
        }
        const announcement = args.join(' ');
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (message.channel && 'send' in message.channel) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            await message.channel.send(`📢 **Announcement**\n\n${announcement}`);
        }
        try {
            await message.delete();
        }
        catch {
            // ignore delete failures
        }
    }
    async handleSayCommand(message, args) {
        const hasPerm = message.member?.permissions.has(PermissionFlagsBits.ManageMessages);
        if (!hasPerm) {
            await message.reply('You need Manage Messages permissions to use this command.');
            return;
        }
        if (args.length === 0) {
            await message.reply('Please provide a message. Usage: `!say <message>`');
            return;
        }
        const text = args.join(' ');
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if (message.channel && 'send' in message.channel) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            await message.channel.send(text);
        }
        try {
            await message.delete();
        }
        catch {
            // ignore delete failures
        }
    }
    async handleConfigCommand(message) {
        const hasPerm = message.member?.permissions.has(PermissionFlagsBits.Administrator);
        if (!hasPerm) {
            await message.reply('You need Administrator permissions to use this command.');
            return;
        }
        const config = await this.storage.getBotConfig();
        const autoMessages = await this.storage.getAutoMessages();
        const activeMessages = autoMessages.filter((msg) => msg.isEnabled).length;
        await message.reply(`🤖 **Bot Configuration**\n` +
            `**Prefix:** ${config?.prefix || '!'}\n` +
            `**Status:** ${this.isReady ? '✅ Online' : '❌ Offline'}\n` +
            `**Active Auto-Messages:** ${activeMessages}\n` +
            `**Servers:** ${this.client.guilds.cache.size}\n\n` +
            `Visit the web dashboard for advanced configuration.`);
    }
    async syncServers() {
        const guilds = Array.from(this.client.guilds.cache.values());
        for (const guild of guilds) {
            const existingServer = await this.storage.getDiscordServer(guild.id);
            if (!existingServer) {
                await this.storage.createDiscordServer({
                    id: guild.id,
                    name: guild.name,
                    memberCount: guild.memberCount?.toString(),
                    iconUrl: guild.iconURL() ?? undefined,
                    isActive: true,
                });
            }
            else {
                await this.storage.updateDiscordServer(guild.id, {
                    name: guild.name,
                    memberCount: guild.memberCount?.toString(),
                    iconUrl: guild.iconURL() ?? undefined,
                    isActive: true,
                });
            }
        }
    }
    async addServer(guild) {
        await this.storage.createDiscordServer({
            id: guild.id,
            name: guild.name,
            memberCount: guild.memberCount?.toString(),
            iconUrl: guild.iconURL() ?? undefined,
            isActive: true,
        });
    }
    async updateStats() {
        const servers = await this.storage.getDiscordServers();
        const activeServers = servers.filter((s) => s.isActive).length;
        await this.storage.updateBotStats({
            activeServers: activeServers.toString(),
        });
    }
    async incrementMessagesSent() {
        const stats = await this.storage.getBotStats();
        const newCount = (parseInt(stats.totalMessagesSent) + 1).toString();
        await this.storage.updateBotStats({
            totalMessagesSent: newCount,
            autoReplyRate: '98.5',
        });
    }
    async incrementCommandsUsed() {
        const stats = await this.storage.getBotStats();
        const newCount = (parseInt(stats.commandsUsed) + 1).toString();
        await this.storage.updateBotStats({
            commandsUsed: newCount,
        });
    }
    getClient() {
        return this.client;
    }
    isOnline() {
        return this.isReady;
    }
}
// Main Application
async function main() {
    const storage = new MemoryStorage();
    const discordBot = new DiscordBot(storage);
    // Express App Setup
    const app = express();
    app.use(express.json());
    app.use(express.urlencoded({ extended: false }));
    // API Routes
    app.get('/api/bot/config', async (_req, res) => {
        try {
            const config = await storage.getBotConfig();
            if (!config) {
                return res.json({ token: '', prefix: '!', isActive: false });
            }
            return res.json({ ...config, token: config.token ? '***' : '' });
        }
        catch (error) {
            return res
                .status(500)
                .json({ message: 'Failed to fetch bot configuration' });
        }
    });
    app.post('/api/bot/config', async (req, res) => {
        try {
            const { token, prefix, isActive } = req.body ?? {};
            const existingConfig = await storage.getBotConfig();
            let config;
            if (existingConfig) {
                config = await storage.updateBotConfig(existingConfig.id, {
                    token,
                    prefix,
                    isActive,
                });
            }
            else {
                config = await storage.createBotConfig({
                    token,
                    prefix: prefix || '!',
                    isActive: isActive ?? true,
                });
            }
            if (token) {
                await discordBot.stop();
                await discordBot.start();
            }
            return res.json(config);
        }
        catch (error) {
            return res.status(400).json({ message: 'Invalid bot configuration data' });
        }
    });
    app.get('/api/bot/status', async (_req, res) => {
        try {
            const isOnline = discordBot.isOnline();
            const client = discordBot.getClient();
            const uptimeMs = client.uptime ?? 0;
            const uptimeSeconds = Math.floor(uptimeMs / 1000);
            return res.json({
                isOnline,
                uptime: `${Math.floor(uptimeSeconds / 3600)}h ${Math.floor((uptimeSeconds % 3600) / 60)}m`,
                serverCount: client.guilds?.cache.size || 0,
            });
        }
        catch (error) {
            return res.status(500).json({ message: 'Failed to fetch bot status' });
        }
    });
    app.get('/api/messages', async (_req, res) => {
        const messages = await storage.getAutoMessages();
        return res.json(messages);
    });
    app.post('/api/messages', async (req, res) => {
        try {
            const message = await storage.createAutoMessage(req.body);
            return res.json(message);
        }
        catch (error) {
            return res.status(400).json({ message: 'Invalid message data' });
        }
    });
    app.put('/api/messages/:id', async (req, res) => {
        const { id } = req.params;
        const message = await storage.updateAutoMessage(id, req.body);
        if (!message) {
            return res.status(404).json({ message: 'Message not found' });
        }
        return res.json(message);
    });
    app.delete('/api/messages/:id', async (req, res) => {
        const { id } = req.params;
        const deleted = await storage.deleteAutoMessage(id);
        if (!deleted) {
            return res.status(404).json({ message: 'Message not found' });
        }
        return res.json({ message: 'Message deleted successfully' });
    });
    app.get('/api/servers', async (_req, res) => {
        const servers = await storage.getDiscordServers();
        return res.json(servers);
    });
    app.get('/api/logs', async (req, res) => {
        const limit = req.query.limit ? parseInt(req.query.limit) : 50;
        const logs = await storage.getCommandLogs(limit);
        return res.json(logs);
    });
    app.get('/api/stats', async (_req, res) => {
        const stats = await storage.getBotStats();
        return res.json(stats);
    });
    // Simple HTML Interface
    app.get('/', (_req, res) => {
        res.send(`
<!DOCTYPE html>
<html>
<head>
    <title>Discord Bot Manager</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .config { background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }
        input, textarea, button { margin: 5px; padding: 8px; }
        button { background: #5865f2; color: white; border: none; border-radius: 3px; cursor: pointer; }
        button:hover { background: #4752c4; }
        .status { padding: 10px; border-radius: 3px; margin: 10px 0; }
        .online { background: #d4edda; color: #155724; }
        .offline { background: #f8d7da; color: #721c24; }
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body>
    <h1>🤖 Discord Bot Manager</h1>
    
    <div class="config">
        <h3>Bot Configuration</h3>
        <input type="text" id="token" placeholder="Discord Bot Token" style="width: 300px;">
        <input type="text" id="prefix" placeholder="Command Prefix" value="!" style="width: 50px;">
        <button onclick="saveConfig()">Save Config</button>
    </div>

    <div id="status" class="status offline">Bot Status: Offline</div>

    <div class="config">
        <h3>Create Auto-Reply Message</h3>
        <input type="text" id="messageName" placeholder="Message Name" style="width: 200px;"><br>
        <textarea id="messageContent" placeholder="Reply Message" rows="3" style="width: 400px;"></textarea><br>
        <select id="messageType">
            <option value="dm_reply">DM Auto-Reply</option>
            <option value="announcement">Announcement</option>
            <option value="welcome">Welcome Message</option>
        </select>
        <select id="triggerCondition">
            <option value="any_dm">Any DM</option>
            <option value="keywords">Keywords</option>
            <option value="first_message">First Message</option>
        </select><br>
        <input type="text" id="keywords" placeholder="Keywords (comma-separated)" style="width: 300px;"><br>
        <button onclick="createMessage()">Create Message</button>
    </div>

    <div id="messages"></div>

    <script>
        async function saveConfig() {
            const token = document.getElementById('token').value;
            const prefix = document.getElementById('prefix').value;
            
            await fetch('/api/bot/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, prefix, isActive: true })
            });
            
            alert('Configuration saved!');
            updateStatus();
        }

        async function createMessage() {
            const name = document.getElementById('messageName').value;
            const content = document.getElementById('messageContent').value;
            const messageType = document.getElementById('messageType').value;
            const triggerCondition = document.getElementById('triggerCondition').value;
            const keywordsInput = document.getElementById('keywords').value;
            const keywords = keywordsInput ? keywordsInput.split(',').map(k => k.trim()) : [];

            await fetch('/api/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name, content, messageType, triggerCondition, keywords, isEnabled: true
                })
            });

            alert('Message created!');
            loadMessages();
        }

        async function updateStatus() {
            const response = await fetch('/api/bot/status');
            const status = await response.json();
            const statusDiv = document.getElementById('status');
            
            if (status.isOnline) {
                statusDiv.className = 'status online';
                statusDiv.textContent = 'Bot Status: Online (Uptime: ' + status.uptime + ', Servers: ' + status.serverCount + ')';
            } else {
                statusDiv.className = 'status offline';
                statusDiv.textContent = 'Bot Status: Offline';
            }
        }

        async function loadMessages() {
            const response = await fetch('/api/messages');
            const messages = await response.json();
            const messagesDiv = document.getElementById('messages');
            
            messagesDiv.innerHTML = '<h3>Auto-Messages</h3>' + 
                messages.map(function (msg) {
                    return '' +
                        '<div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0;">' +
                        '<strong>' + msg.name + '</strong> (' + msg.messageType + ') - ' +
                        '<span style="color: ' + (msg.isEnabled ? 'green' : 'red') + '">' +
                        (msg.isEnabled ? 'Enabled' : 'Disabled') +
                        '</span><br>' +
                        '<em>' + msg.content + '</em>' +
                        '</div>';
                }).join('');
        }

        // Update status every 5 seconds
        setInterval(updateStatus, 5000);
        updateStatus();
        loadMessages();
    </script>
</body>
</html>
    `);
    });
    // Start Discord Bot
    const botToken = process.env.DISCORD_BOT_TOKEN || process.env.BOT_TOKEN;
    if (botToken) {
        await storage.createBotConfig({
            token: botToken,
            prefix: '!',
            isActive: true,
        });
        await discordBot.start();
    }
    else {
        console.warn('No Discord bot token provided. Bot will not start automatically.');
        console.log('Set DISCORD_BOT_TOKEN or BOT_TOKEN environment variable, or configure via web interface.');
    }
    // Start Server
    const port = parseInt(process.env.PORT || '3000', 10);
    const server = createServer(app);
    server.listen(port, '0.0.0.0', () => {
        console.log(`🚀 Discord Bot Manager running on http://localhost:${port}`);
        console.log(`📝 Configure your bot at http://localhost:${port}`);
    });
    // Handle graceful shutdown
    process.on('SIGINT', async () => {
        console.log('Shutting down gracefully...');
        try {
            await discordBot.stop();
        }
        finally {
            server.close(() => process.exit(0));
        }
    });
}
// Start the application
main().catch((err) => {
    console.error(err);
    process.exit(1);
});
