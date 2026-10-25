def create_driver(self, config: Dict[str, Any]) -> bool:
        """
        创建浏览器驱动

        Args:
            config: 浏览器配置

        Returns:
            是否创建成功
        """
        try:
            self.logger.info("开始创建浏览器驱动")

            headless = config.get("headless", True)
            chrome_major = detect_chrome_major_version()

            def build_options():
                """创建一个新的 ChromeOptions 实例，避免重复复用同一个对象。"""
                if UNDETECTED_AVAILABLE:
                    self.logger.info("使用undetected-chromedriver创建浏览器")
                    options = uc.ChromeOptions()
                else:
                    self.logger.info("使用标准selenium创建浏览器")
                    options = Options()

                # 基础配置
                if headless:
                    options.add_argument("--headless")
                    self.logger.debug("启用无头模式")
                else:
                    self.logger.debug("使用有头模式（显示浏览器窗口）")

                browser_args = [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "--disable-popup-blocking",
                ]

                if os.getenv("GITHUB_ACTIONS") or os.getenv("CI"):
                    self.logger.debug("检测到CI环境，添加额外配置")
                    ci_args = [
                        "--disable-gpu",
                        "--disable-software-rasterizer",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-default-apps",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-sync",
                        "--disable-translate",
                        "--hide-scrollbars",
                        "--mute-audio",
                        "--no-zygote",
                        "--disable-background-networking",
                        "--disable-web-security",
                        "--allow-running-insecure-content",
                        "--window-size=1920,1080",
                        "--font-render-hinting=none",
                        "--disable-font-subpixel-positioning",
                        "--force-device-scale-factor=1",
                    ]
                    browser_args.extend(ci_args)

                for arg in browser_args:
                    options.add_argument(arg)
                    self.logger.debug(f"添加浏览器参数: {arg}")

                prefs = {
                    "profile.default_content_setting_values": {"popups": 1},
                    "webkit.webprefs.fonts.standard.Hans": "SimSun",
                    "webkit.webprefs.fonts.serif.Hans": "SimSun",
                    "webkit.webprefs.fonts.sansserif.Hans": "SimHei",
                    "webkit.webprefs.fonts.cursive.Hans": "SimSun",
                    "webkit.webprefs.fonts.fantasy.Hans": "SimSun",
                    "webkit.webprefs.fonts.pictograph.Hans": "SimSun",
                    "webkit.webprefs.default_encoding": "UTF-8",
                }

                if os.getenv("GITHUB_ACTIONS") or os.getenv("CI"):
                    ci_font_prefs = {
                        "webkit.webprefs.fonts.standard.Hans": "Noto Sans CJK SC",
                        "webkit.webprefs.fonts.serif.Hans": "Noto Serif CJK SC",
                        "webkit.webprefs.fonts.sansserif.Hans": "Noto Sans CJK SC",
                        "webkit.webprefs.fonts.cursive.Hans": "Noto Sans CJK SC",
                        "webkit.webprefs.fonts.fantasy.Hans": "Noto Sans CJK SC",
                        "webkit.webprefs.fonts.pictograph.Hans": "Noto Sans CJK SC",
                    }
                    prefs.update(ci_font_prefs)
                    self.logger.debug("配置CI环境中文字体偏好")

                options.add_experimental_option("prefs", prefs)
                self.logger.debug("配置浏览器偏好设置: 弹出窗口允许、中文字体支持")

                browser_binary = resolve_chrome_binary()
                if browser_binary:
                    options.binary_location = browser_binary
                    self.logger.debug(f"设置 Chrome 二进制路径: {browser_binary}")

                if chrome_major:
                    self.logger.info(f"检测到 Chrome 版本: {chrome_major}")

                return options

            def create_browser_with_options(options):
                if UNDETECTED_AVAILABLE:
                    if chrome_major:
                        return uc.Chrome(options=options, version_main=chrome_major)
                    return uc.Chrome(options=options)

                driver_path = install_chromedriver_for_current_chrome()
                if driver_path:
                    return webdriver.Chrome(service=Service(driver_path), options=options)
                return webdriver.Chrome(options=options)

            self.logger.debug("开始初始化浏览器实例")
            try:
                options = build_options()
                raw_driver = create_browser_with_options(options)
            except Exception as driver_error:
                self.logger.warning(f"首次创建浏览器失败，尝试回退方案: {driver_error}")
                try:
                    options = build_options()
                    raw_driver = create_browser_with_options(options)
                except Exception as retry_error:
                    raise WebDriverException(f"创建浏览器驱动失败: {retry_error}") from retry_error

            # 使用安全包装器
            self.driver = SafeChrome(raw_driver)
            self.wait = WebDriverWait(self.driver, 10)

            try:
                browser_version = self.driver.capabilities.get("browserVersion", "Unknown")
                driver_version = self.driver.capabilities.get("chrome", {}).get(
                    "chromedriverVersion", "Unknown"
                )
                self.logger.debug(f"浏览器版本: {browser_version}")
                self.logger.debug(f"驱动版本: {driver_version}")
            except Exception as e:
                self.logger.debug(f"获取浏览器信息失败: {e}")

            self.logger.info("浏览器驱动创建成功")
            return True

        except Exception as e:
            self.logger.error(f"创建浏览器驱动失败: {e}")
            return False
