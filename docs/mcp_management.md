# 🔌 MCP Server Management Guide

OrionAI includes a comprehensive **Model Context Protocol (MCP) Server Management System** that provides access to **396+ external tools and services** through an intuitive menu-driven interface.

## 🚀 Quick Start

1. **Launch OrionAI CLI**:
   ```bash
   orionai
   ```

2. **Select option 5**: "📦 Install External MCP Servers"

3. **Browse and install servers** from 12+ categories with 396+ available options

## 📦 Available Server Categories

### 🔍 Web Search & Information (44 servers)
- **DuckDuckGo Search** - Privacy-focused web search
- **Exa Search** - Semantic web search with AI
- **Tavily Search** - Real-time search API
- **Google Search** - Traditional Google search
- **Academic Paper Search** - Scholarly article discovery
- **News Search** - Real-time news aggregation
- **Wikipedia Search** - Knowledge base queries

### 💻 Development Tools (346 servers)
- **GitHub Integration** - Repository management, issues, PRs
- **GitLab Tools** - Project management and CI/CD
- **Terminal Controller** - Remote command execution
- **CircleCI Integration** - Continuous integration
- **Docker Management** - Container operations
- **Code Analysis** - Static analysis and linting
- **API Testing** - REST/GraphQL endpoint testing

### 🔢 Calculators & Math (6 servers)
- **Scientific Calculator** - Advanced mathematical operations
- **Solver Tools** - Equation and constraint solving
- **Statistics Calculator** - Statistical analysis tools
- **Unit Converter** - Measurement conversions
- **Mathematical Graphing** - Function plotting and visualization

### 🗄️ Database & Storage
- **ClickHouse** - High-performance analytics database
- **Elasticsearch** - Search and analytics engine
- **MongoDB** - NoSQL document database
- **PostgreSQL** - Relational database operations
- **Chroma** - Vector database for AI applications
- **Box Cloud Storage** - File storage and sharing
- **Database Query Tools** - Multi-database SQL interface

### 📱 Social Media Integration
- **Twitter/X API** - Social media posting and analytics
- **Instagram Tools** - Content management
- **LinkedIn Integration** - Professional networking
- **Reddit API** - Community interaction
- **Social Analytics** - Cross-platform metrics

### 📋 Productivity & Tasks
- **Todoist** - Task management and organization
- **Calendar Integration** - Schedule management
- **Note-taking Tools** - Information capture
- **Project Management** - Team collaboration
- **Time Tracking** - Productivity monitoring

### 💰 Finance & Business
- **Stripe Integration** - Payment processing
- **Banking APIs** - Financial data access
- **Currency Conversion** - Real-time exchange rates
- **Invoice Management** - Billing automation
- **Expense Tracking** - Financial monitoring

### 🎵 Media & Entertainment
- **Spotify Integration** - Music streaming controls
- **YouTube API** - Video management
- **Image Processing** - Photo editing and analysis
- **Audio Tools** - Sound processing
- **Media Analytics** - Content performance metrics

### 🤖 AI & Machine Learning
- **Model Monitoring** - AI performance tracking
- **Training Tools** - ML pipeline management
- **Arize Phoenix** - AI observability platform
- **Model Registry** - Version control for ML models
- **Data Labeling** - Dataset preparation

### 🛠️ Utilities
- **Weather Services** - Global weather data
- **Time Zone Tools** - World clock and conversions
- **Translation Services** - Multi-language support
- **QR Code Generator** - Barcode creation
- **File Converters** - Format transformations

### 🌐 Web Tools
- **HTTP Client** - REST API interactions
- **Webhook Handlers** - Event processing
- **Web Scraping** - Data extraction
- **URL Shorteners** - Link management
- **Website Monitoring** - Uptime tracking

### ☁️ Cloud Storage
- **AWS S3** - Object storage
- **Google Drive** - File synchronization
- **Dropbox** - Cloud file storage
- **OneDrive** - Microsoft cloud integration
- **FTP/SFTP** - File transfer protocols

## 🎯 How to Use

### 1. Browse All Servers
- View all 396+ servers with pagination
- See server details, requirements, and descriptions
- Navigate through pages of available tools

### 2. Browse by Category
- Explore servers organized by functionality
- Focus on specific use cases (search, development, etc.)
- See server counts per category

### 3. Search Servers
- Find servers by name or description
- Quick discovery of specific functionality
- Filter results by keywords

### 4. Select Multiple Servers
- Build a custom installation queue
- Select servers from different categories
- Review selections before installation

### 5. Automated Installation
- **Dependency checking** - Verifies Node.js, Python, Docker
- **Package installation** - NPM, PyPI, and OCI containers
- **API key configuration** - Guided setup for external services
- **Progress tracking** - Real-time installation status

### 6. Configuration Generation
- **Claude Desktop integration** - Auto-generated config files
- **Environment variables** - Template for API keys
- **Usage instructions** - Comprehensive setup guide

## 🔑 API Key Management

Many servers require API keys from external services:

### Common API Services
- **Search APIs**: Exa, Tavily, Google
- **Social Media**: Twitter, Instagram, LinkedIn
- **Productivity**: Todoist, Notion, Calendly
- **Finance**: Stripe, banking providers
- **Weather**: OpenWeatherMap, AccuWeather
- **Translation**: Google Translate, DeepL
- **Cloud Services**: AWS, Google Cloud, Azure

### API Key Setup Process
1. **Server selection** - Choose servers requiring API keys
2. **Service identification** - See which external services are needed
3. **Guided configuration** - Step-by-step API key entry
4. **Secure storage** - Encrypted local storage
5. **Configuration templates** - Ready-to-use environment files

## 🛠️ Technical Requirements

### Supported Installation Methods
- **NPM packages** - Node.js based servers
- **PyPI packages** - Python based servers  
- **OCI containers** - Docker based servers

### Dependencies
- **Node.js & npm** - For JavaScript/TypeScript servers
- **Python & pip** - For Python servers (automatically available)
- **Docker** - For containerized servers
- **Git** - For repository-based installations

### System Requirements
- **Operating System**: Windows, macOS, Linux
- **Python**: 3.8 or higher
- **Memory**: 2GB RAM minimum
- **Storage**: 1GB for server installations
- **Network**: Internet connection for downloads

## 📋 Installation Flow Example

```
🚀 OrionAI MCP Manager
┌─────────────────────────────────────┐
│ 1. Browse servers by category       │
│ 2. Search for "weather" servers     │
│ 3. Select OpenWeatherMap server     │
│ 4. Add Exa search server           │
│ 5. Add GitHub integration server    │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ Dependency Check                    │
│ ✅ Python available                │
│ ✅ Node.js detected                │
│ ⚠️  Docker not found               │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ API Key Configuration               │
│ 🔑 OpenWeatherMap API key          │
│ 🔑 Exa API key                     │
│ 🔑 GitHub token                    │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ Installation                        │
│ 📦 Installing servers...           │
│ ✅ OpenWeatherMap (PyPI)           │
│ ✅ Exa Search (NPM)                │
│ ✅ GitHub Tools (PyPI)             │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ Configuration Generated             │
│ 📄 claude_desktop_config.json      │
│ 🔑 api_keys.json                   │
│ 📖 usage_instructions.md           │
└─────────────────────────────────────┘
```

## 🎮 Interactive Features

### Rich Terminal Interface
- **Color-coded categories** - Easy visual navigation
- **Progress indicators** - Real-time installation progress
- **Status indicators** - Installed/Available/Selected states
- **Pagination** - Handle large server lists efficiently
- **Search highlighting** - Quick result identification

### Smart Selection
- **Batch operations** - Select multiple servers at once
- **Dependency awareness** - Automatic requirement detection
- **Conflict detection** - Prevent incompatible combinations
- **Resource estimation** - Storage and memory requirements

### Error Handling
- **Graceful failures** - Continue with other servers if one fails
- **Retry mechanisms** - Automatic retry for network issues
- **Detailed logging** - Comprehensive error reporting
- **Recovery options** - Manual intervention when needed

## 📊 Usage Statistics

After installation, you can view:
- **Total servers installed** - Count of active tools
- **Categories covered** - Functional areas available
- **API services configured** - External integrations
- **Storage usage** - Disk space consumed
- **Last update** - Installation timestamp

## 🔧 Advanced Configuration

### Custom Server Sources
- **Private registries** - Corporate MCP servers
- **Local development** - Custom server testing
- **Alternative registries** - Third-party server collections

### Configuration Management
- **Profile support** - Multiple configuration sets
- **Export/import** - Share configurations
- **Backup/restore** - Configuration versioning
- **Selective updates** - Update individual servers

## 🚨 Troubleshooting

### Common Issues
1. **Network connectivity** - Check internet connection
2. **Permission errors** - Run with appropriate privileges
3. **API key issues** - Verify key validity and permissions
4. **Dependency conflicts** - Update Node.js/Python versions
5. **Storage limitations** - Free up disk space

### Support Resources
- **Built-in help** - Comprehensive CLI help system
- **Error diagnostics** - Detailed error reporting
- **Log files** - Installation and execution logs
- **Community support** - GitHub discussions and issues

## 🎯 Best Practices

### Server Selection Strategy
1. **Start small** - Install a few essential servers first
2. **Test functionality** - Verify each server works before adding more
3. **Monitor resources** - Track system performance impact
4. **Regular updates** - Keep servers current with latest versions

### API Key Security
1. **Limit permissions** - Use minimal required access levels
2. **Regular rotation** - Update keys periodically
3. **Secure storage** - Use encrypted configuration files
4. **Access monitoring** - Track API usage patterns

### Maintenance
1. **Regular cleanup** - Remove unused servers
2. **Configuration review** - Update settings as needed
3. **Performance monitoring** - Track system resource usage
4. **Backup configurations** - Save working setups

---

## 🚀 Getting Started

Ready to enhance your AI assistant with 396+ external tools?

```bash
# Launch OrionAI CLI
orionai

# Select option 5: "📦 Install External MCP Servers"
# Browse, select, and install your desired tools!
```

Transform your AI assistant into a comprehensive productivity platform with access to web search, databases, development tools, social media, productivity apps, and much more!
