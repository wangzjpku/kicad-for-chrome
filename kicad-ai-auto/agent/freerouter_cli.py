"""
FreeRouter CLI 启动器
尝试查找并使用 FreeRouter 的命令行模式

注意: FreeRouting 官方版本需要 GUI 交互
此模块提供后备方案和更好的错误提示
"""

import os
import sys
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class FreeRouterCLI:
    """FreeRouter 命令行接口"""

    # 可能的 FreeRouter 路径
    POSSIBLE_PATHS = [
        # 用户目录
        Path.home() / "FreeRouter" / "freerouter.jar",
        Path.home() / ".local" / "share" / "freerouter" / "freerouter.jar",
        # KiCad 目录
        Path("C:/Program Files/KiCad/9.0") / "freerouter" / "freerouter.jar",
        Path("E:/Program Files/KiCad/9.0") / "freerouter" / "freerouter.jar",
        # 项目目录
        Path(__file__).parent.parent / "tools" / "freerouter.jar",
    ]

    def __init__(self, freerouter_path: str = None):
        self.freerouter_jar = None

        if freerouter_path:
            self.freerouter_jar = Path(freerouter_path)
        else:
            # 自动查找
            for path in self.POSSIBLE_PATHS:
                if path.exists():
                    self.freerouter_jar = path
                    logger.info(f"找到 FreeRouter: {path}")
                    break

        self.java_path = self._find_java()

    def _find_java(self) -> Optional[str]:
        """查找 Java 运行时"""
        java_paths = [
            "java",
            "C:/Program Files/Java/jre/bin/java.exe",
            "C:/Program Files/Java/jdk/bin/java.exe",
        ]

        for java in java_paths:
            try:
                result = subprocess.run(
                    [java, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"找到 Java: {java}")
                    return java
            except Exception as e:
                logger.debug(f"查找Java路径失败: {e}")
                continue

        return None

    def is_available(self) -> bool:
        """检查 FreeRouter 是否可用"""
        return self.freerouter_jar is not None and self.java_path is not None

    def execute(
        self,
        dsn_path: str,
        output_ses_path: str = None,
        timeout: int = 120,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Execute FreeRouter with a DSN file and produce SES output.

        Args:
            dsn_path: Path to input Specctra DSN file
            output_ses_path: Path for output SES file (default: same dir as DSN)
            timeout: Maximum execution time in seconds
            progress_callback: Optional callback(progress_pct, message) for progress updates

        Returns:
            Dict with success, ses_path, stats, message
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "FreeRouter not available",
                "fallback": "Use SimpleAutoRouter (push-and-shove)",
            }

        dsn = Path(dsn_path)
        if not dsn.exists():
            return {"success": False, "error": f"DSN file not found: {dsn_path}"}

        if output_ses_path is None:
            output_ses_path = str(dsn.with_suffix(".ses"))

        try:
            cmd = [
                self.java_path,
                "-jar", str(self.freerouter_jar),
                dsn_path,
                "-o", output_ses_path,
            ]

            logger.info(f"Executing FreeRouter: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(dsn.parent),
            )

            # Monitor progress from stdout
            stats = {"nets_total": 0, "nets_routed": 0, "vias": 0, "progress_pct": 0}
            start_time = time.time()

            while True:
                line = process.stdout.readline()
                if not line:
                    # Check if process ended
                    if process.poll() is not None:
                        break
                    # Timeout check
                    if time.time() - start_time > timeout:
                        process.kill()
                        return {
                            "success": False,
                            "error": f"FreeRouter timed out after {timeout}s",
                        }
                    continue

                line = line.strip()
                if not line:
                    continue

                # Parse FreeRouter progress output
                if "routing net" in line.lower():
                    stats["nets_total"] += 1
                    if "routed" in line.lower() or "complete" in line.lower():
                        stats["nets_routed"] += 1
                elif "vias:" in line.lower() or "vias added" in line.lower():
                    try:
                        via_count = int("".join(c for c in line.split(":")[-1] if c.isdigit()))
                        stats["vias"] = via_count
                    except (ValueError, IndexError):
                        pass
                elif "%" in line:
                    try:
                        pct_str = line.split("%")[0].split()[-1]
                        stats["progress_pct"] = float(pct_str)
                    except (ValueError, IndexError):
                        pass

                if progress_callback and stats["progress_pct"] > 0:
                    progress_callback(stats["progress_pct"], line)

            # Process completed
            returncode = process.poll()
            stderr_output = process.stderr.read()

            if returncode != 0:
                logger.error(f"FreeRouter exited with code {returncode}: {stderr_output[:500]}")
                return {
                    "success": False,
                    "error": f"FreeRouter exited with code {returncode}",
                    "stderr": stderr_output[:500],
                }

            ses_path = Path(output_ses_path)
            if not ses_path.exists():
                # FreeRouter may write SES alongside DSN with .ses extension
                alt_ses = dsn.with_suffix(".ses")
                if alt_ses.exists():
                    output_ses_path = str(alt_ses)
                else:
                    return {
                        "success": False,
                        "error": "FreeRouter completed but no SES output found",
                        "stderr": stderr_output[:500],
                    }

            elapsed = time.time() - start_time
            logger.info(f"FreeRouter completed in {elapsed:.1f}s: {output_ses_path}")

            return {
                "success": True,
                "ses_path": output_ses_path,
                "elapsed_seconds": round(elapsed, 1),
                "stats": stats,
                "message": f"Routed {stats['nets_routed']}/{stats['nets_total']} nets in {elapsed:.1f}s",
            }

        except FileNotFoundError:
            return {"success": False, "error": "Java executable not found"}
        except Exception as e:
            logger.error(f"FreeRouter execution error: {e}")
            return {"success": False, "error": str(e)}

    def route_via_freerouter(self, board, timeout: int = 120, progress_callback=None) -> Dict[str, Any]:
        """
        Full pipeline: export board to DSN → run FreeRouter → import SES.

        Args:
            board: Board object with nets, tracks, footprints
            timeout: FreeRouter execution timeout in seconds
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with success, tracks, vias, stats
        """
        import tempfile

        if not self.is_available():
            return {
                "success": False,
                "error": "FreeRouter not available",
                "fallback": "Use SimpleAutoRouter (push-and-shove)",
            }

        try:
            from routing.dsn_exporter import DSNExporter
            from routing.ses_importer import SESImporter
        except ImportError as e:
            return {"success": False, "error": f"Missing module: {e}"}

        # Step 1: Export DSN
        with tempfile.TemporaryDirectory(prefix="freerouter_") as tmpdir:
            dsn_path = os.path.join(tmpdir, "board.dsn")

            try:
                exporter = DSNExporter()
                exporter.export_to_file(board, dsn_path)
            except Exception as e:
                return {"success": False, "error": f"DSN export failed: {e}"}

            # Step 2: Execute FreeRouter
            result = self.execute(dsn_path, timeout=timeout, progress_callback=progress_callback)
            if not result.get("success"):
                return result

            # Step 3: Import SES
            try:
                importer = SESImporter()
                importer.parse(result["ses_path"])
                tracks = importer.to_kicad_tracks()
                vias = importer.to_kicad_vias()
            except Exception as e:
                return {"success": False, "error": f"SES import failed: {e}"}

            return {
                "success": True,
                "method": "freerouter",
                "tracks": tracks,
                "vias": vias,
                "track_count": len(tracks),
                "via_count": len(vias),
                "elapsed_seconds": result.get("elapsed_seconds", 0),
                "freerouter_stats": result.get("stats", {}),
            }

    def get_status(self) -> Dict[str, Any]:
        """获取 FreeRouter 状态"""
        status = {
            "available": self.is_available(),
            "jar_path": str(self.freerouter_jar) if self.freerouter_jar else None,
            "java_path": self.java_path,
            "note": ""
        }

        if not status["available"]:
            if not self.freerouter_jar:
                status["note"] = "FreeRouter JAR 未找到"
            elif not self.java_path:
                status["note"] = "Java 运行时未找到"

        return status


class SimpleAutoRouter:
    """
    简单的自动布线器
    实现基于 A* 算法的自动布线
    """

    def __init__(self):
        self.board = None
        self.push_router = None

    def set_board(self, board):
        """设置 PCB 板对象"""
        self.board = board

    def route_all(self) -> Dict[str, Any]:
        """
        对所有网络进行自动布线
        使用 A* 算法和推挤式策略
        """
        if not self.board:
            return {
                "success": False,
                "error": "No board loaded"
            }

        try:
            # 导入推挤式布线器
            from routing.push_router import get_push_router, Segment, Point, Obstacle

            # 获取所有网络
            nets = self.board.nets
            if not nets:
                return {
                    "success": False,
                    "error": "No nets found on board"
                }

            logger.info(f"开始自动布线，总网络数: {len(nets)}")

            # 初始化推挤路由器
            self.push_router = get_push_router()
            self.push_router.clear_obstacles()

            # 收集现有走线作为障碍物
            existing_tracks = self.board.tracks
            for track in existing_tracks:
                try:
                    seg = Segment(
                        start=Point(track.start.x, track.start.y),
                        end=Point(track.end.x, track.end.y),
                        layer=track.layer,
                        width=track.width,
                    )
                    self.push_router.add_obstacle(Obstacle(segment=seg, priority=1))
                except Exception as e:
                    logger.debug(f"跳过障碍物: {e}")

            # 收集焊盘位置
            footprints = self.board.footprints
            pads = []
            for fp in footprints:
                try:
                    for pad in fp.pads:
                        pads.append({
                            "position": (pad.position.x, pad.position.y),
                            "net": pad.net,
                            "layer": pad.layer,
                        })
                except Exception as e:
                    logger.debug(f"跳过焊盘: {e}")

            routed_count = 0
            failed_nets = []
            total_length = 0.0
            total_vias = 0

            # 对每个网络布线
            for net in nets[:50]:  # 限制最多50个网络
                try:
                    if not net or not net.items:
                        continue

                    # 获取网络的焊盘
                    net_pads = [p for p in pads if p["net"] == net.name]
                    if len(net_pads) < 2:
                        continue

                    # 使用推挤路由器布线
                    start = net_pads[0]["position"]
                    end = net_pads[1]["position"]

                    result = self.push_router.route(
                        start=start,
                        end=end,
                        start_layer=net_pads[0].get("layer", "F.Cu"),
                        end_layer=net_pads[1].get("layer", "F.Cu"),
                        net_name=net.name,
                    )

                    if result.success:
                        routed_count += 1
                        total_length += result.total_length
                        total_vias += result.via_count
                    else:
                        failed_nets.append(net.name)

                except Exception as e:
                    logger.debug(f"网络 {net.name if net else 'unknown'} 布线失败: {e}")
                    if net:
                        failed_nets.append(net.name)

            logger.info(f"自动布线完成: 成功 {routed_count}, 失败 {len(failed_nets)}")

            return {
                "success": True,
                "method": "push_router",
                "message": f"Routed {routed_count} nets successfully",
                "routed_count": routed_count,
                "failed_count": len(failed_nets),
                "failed_nets": failed_nets[:10],  # 最多返回10个
                "total_length": round(total_length, 2),
                "total_vias": total_vias,
            }

        except ImportError as e:
            logger.error(f"导入推挤路由器失败: {e}")
            return {
                "success": False,
                "error": "Push router not available",
                "hint": "请确保 routing.push_router 模块已安装"
            }
        except Exception as e:
            logger.error(f"自动布线错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def route_net(self, net_name: str) -> Dict[str, Any]:
        """对指定网络布线"""
        if not self.board:
            return {"success": False, "error": "No board loaded"}

        try:
            from routing.push_router import get_push_router, Segment, Point, Obstacle

            # 获取指定网络
            net = None
            for n in self.board.nets:
                if n.name == net_name:
                    net = n
                    break

            if not net:
                return {"success": False, "error": f"Net not found: {net_name}"}

            # 获取网络的焊盘
            footprints = self.board.footprints
            pads = []
            for fp in footprints:
                try:
                    for pad in fp.pads:
                        if pad.net == net_name:
                            pads.append({
                                "position": (pad.position.x, pad.position.y),
                                "net": pad.net,
                                "layer": pad.layer,
                            })
                except Exception as e:
                    logger.debug(f"跳过焊盘: {e}")

            if len(pads) < 2:
                return {"success": False, "error": "需要至少2个焊盘"}

            # 使用推挤路由器
            self.push_router = get_push_router()
            self.push_router.clear_obstacles()

            start = pads[0]["position"]
            end = pads[1]["position"]

            result = self.push_router.route(
                start=start,
                end=end,
                start_layer=pads[0].get("layer", "F.Cu"),
                end_layer=pads[1].get("layer", "F.Cu"),
                net_name=net_name,
            )

            return {
                "success": result.success,
                "net": net_name,
                "pads": len(pads),
                "message": result.message,
                "total_length": result.total_length,
                "via_count": result.via_count,
            }

        except Exception as e:
            logger.error(f"网络 {net_name} 布线失败: {e}")
            return {"success": False, "error": str(e)}


def get_router_status() -> Dict[str, Any]:
    """获取路由器状态"""
    freerouter = FreeRouterCLI()
    return {
        "freerouter": freerouter.get_status(),
        "push_router_available": True,
        "simple_router": True,
        "note": "推荐使用 KiCad IPC API 的 /api/kicad-ipc/auto-route 端点进行自动布线"
    }


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)

    status = get_router_status()
    print("路由器状态:")
    for key, value in status.items():
        print(f"  {key}: {value}")
