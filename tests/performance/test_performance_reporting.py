"""
Performance Analysis and Optimization Reporting System

Comprehensive performance reporting with detailed analysis, optimization
recommendations, and actionable insights for performance improvement.
"""

import pytest
import pandas as pd
import numpy as np
import time
import json
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import psutil
from unittest.mock import Mock, patch
import statistics

# Create performance analyzer class
class PerformanceAnalyzer:
    """Analyzes performance test results and provides optimization recommendations"""

    def __init__(self):
        self.test_results = []
        self.benchmark_data = {}
        self.optimization_recommendations = []
        self.performance_trends = {}

    def add_test_result(self, test_name: str, category: str, metrics: Dict[str, Any],
                        data_size: int = None, test_metadata: Dict[str, Any] = None):
        """Add a test result for analysis"""
        result = {
            'test_name': test_name,
            'category': category,
            'timestamp': datetime.now(),
            'metrics': metrics,
            'data_size': data_size,
            'metadata': test_metadata or {}
        }
        self.test_results.append(result)

    def analyze_performance_patterns(self) -> Dict[str, Any]:
        """Analyze performance patterns across all test results"""
        if not self.test_results:
            return {'error': 'No test results available for analysis'}

        analysis = {
            'summary': self._generate_summary(),
            'category_analysis': self._analyze_by_category(),
            'performance_trends': self._analyze_trends(),
            'bottlenecks': self._identify_bottlenecks(),
            'efficiency_metrics': self._calculate_efficiency_metrics(),
            'scalability_analysis': self._analyze_scalability()
        }

        return analysis

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate overall performance summary"""
        total_tests = len(self.test_results)
        categories = list(set(r['category'] for r in self.test_results))

        # Calculate key metrics
        response_times = []
        throughputs = []
        memory_usage = []

        for result in self.test_results:
            metrics = result['metrics']
            if 'duration' in metrics:
                response_times.append(metrics['duration'])
            if 'throughput' in metrics:
                throughputs.append(metrics['throughput'])
            if 'memory_delta_mb' in metrics:
                memory_usage.append(metrics['memory_delta_mb'])

        return {
            'total_tests': total_tests,
            'categories_tested': categories,
            'avg_response_time_ms': np.mean(response_times) * 1000 if response_times else 0,
            'max_response_time_ms': np.max(response_times) * 1000 if response_times else 0,
            'avg_throughput': np.mean(throughputs) if throughputs else 0,
            'max_throughput': np.max(throughputs) if throughputs else 0,
            'avg_memory_usage_mb': np.mean(memory_usage) if memory_usage else 0,
            'max_memory_usage_mb': np.max(memory_usage) if memory_usage else 0,
            'test_completion_rate': 100.0  # Assuming all tests completed
        }

    def _analyze_by_category(self) -> Dict[str, Any]:
        """Analyze performance by category"""
        category_analysis = {}

        for result in self.test_results:
            category = result['category']
            if category not in category_analysis:
                category_analysis[category] = {
                    'test_count': 0,
                    'response_times': [],
                    'throughputs': [],
                    'memory_usage': [],
                    'test_names': []
                }

            analysis = category_analysis[category]
            analysis['test_count'] += 1
            analysis['test_names'].append(result['test_name'])

            metrics = result['metrics']
            if 'duration' in metrics:
                analysis['response_times'].append(metrics['duration'])
            if 'throughput' in metrics:
                analysis['throughputs'].append(metrics['throughput'])
            if 'memory_delta_mb' in metrics:
                analysis['memory_usage'].append(metrics['memory_delta_mb'])

        # Calculate statistics for each category
        for category, data in category_analysis.items():
            if data['response_times']:
                data['avg_response_time'] = np.mean(data['response_times'])
                data['max_response_time'] = np.max(data['response_times'])
                data['response_time_std'] = np.std(data['response_times'])
            else:
                data['avg_response_time'] = data['max_response_time'] = data['response_time_std'] = 0

            if data['throughputs']:
                data['avg_throughput'] = np.mean(data['throughputs'])
                data['min_throughput'] = np.min(data['throughputs'])
                data['max_throughput'] = np.max(data['throughputs'])
            else:
                data['avg_throughput'] = data['min_throughput'] = data['max_throughput'] = 0

            if data['memory_usage']:
                data['avg_memory_usage'] = np.mean(data['memory_usage'])
                data['max_memory_usage'] = np.max(data['memory_usage'])
            else:
                data['avg_memory_usage'] = data['max_memory_usage'] = 0

        return category_analysis

    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        if len(self.test_results) < 5:
            return {'error': 'Insufficient data for trend analysis'}

        # Sort results by timestamp
        sorted_results = sorted(self.test_results, key=lambda x: x['timestamp'])

        trends = {
            'response_time_trend': self._calculate_trend(
                [(r['timestamp'], r['metrics'].get('duration', 0)) for r in sorted_results]
            ),
            'throughput_trend': self._calculate_trend(
                [(r['timestamp'], r['metrics'].get('throughput', 0)) for r in sorted_results]
            ),
            'memory_trend': self._calculate_trend(
                [(r['timestamp'], r['metrics'].get('memory_delta_mb', 0)) for r in sorted_results]
            )
        }

        return trends

    def _calculate_trend(self, data_points):
        """Calculate trend for a series of data points"""
        if len(data_points) < 3:
            return {'slope': 0, 'r_squared': 0, 'trend': 'stable'}

        # Convert timestamps to numeric values (seconds since first point)
        start_time = data_points[0][0]
        x = [(p[0] - start_time).total_seconds() for p in data_points]
        y = [p[1] for p in data_points]

        # Calculate linear regression
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]

        # Calculate R-squared
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Determine trend direction
        if abs(slope) < 0.001:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'

        return {
            'slope': slope,
            'r_squared': r_squared,
            'trend': trend,
            'data_points': len(data_points)
        }

    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []

        # Analyze response times
        response_times = [(r['test_name'], r['metrics'].get('duration', 0))
                          for r in self.test_results if 'duration' in r['metrics']]

        if response_times:
            avg_response_time = np.mean([rt[1] for rt in response_times])
            slow_tests = [(name, time) for name, time in response_times
                         if time > avg_response_time * 1.5]

            for test_name, response_time in slow_tests[:5]:  # Top 5 slowest
                bottlenecks.append({
                    'type': 'slow_response_time',
                    'test_name': test_name,
                    'value': response_time,
                    'severity': 'high' if response_time > avg_response_time * 2 else 'medium',
                    'recommendation': 'Optimize algorithm or increase caching for this test'
                })

        # Analyze memory usage
        memory_usage = [(r['test_name'], r['metrics'].get('memory_delta_mb', 0))
                        for r in self.test_results if 'memory_delta_mb' in r['metrics']]

        if memory_usage:
            avg_memory = np.mean([mu[1] for mu in memory_usage])
            high_memory_tests = [(name, memory) for name, memory in memory_usage
                               if memory > avg_memory * 1.5]

            for test_name, memory in high_memory_tests[:5]:  # Top 5 memory intensive
                bottlenecks.append({
                    'type': 'high_memory_usage',
                    'test_name': test_name,
                    'value': memory,
                    'severity': 'high' if memory > avg_memory * 2 else 'medium',
                    'recommendation': 'Implement memory pooling or reduce memory allocations'
                })

        # Analyze low throughput
        throughputs = [(r['test_name'], r['metrics'].get('throughput', 0))
                      for r in self.test_results if 'throughput' in r['metrics']]

        if throughputs:
            avg_throughput = np.mean([t[1] for t in throughputs])
            low_throughput_tests = [(name, throughput) for name, throughput in throughputs
                                  if throughput < avg_throughput * 0.7]

            for test_name, throughput in low_throughput_tests[:5]:  # Top 5 lowest throughput
                bottlenecks.append({
                    'type': 'low_throughput',
                    'test_name': test_name,
                    'value': throughput,
                    'severity': 'high' if throughput < avg_throughput * 0.5 else 'medium',
                    'recommendation': 'Parallelize operations or optimize data structures'
                })

        return bottlenecks

    def _calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate efficiency metrics"""
        efficiency_metrics = {}

        # Calculate memory efficiency
        memory_tests = [r for r in self.test_results if 'memory_delta_mb' in r['metrics']
                        and r.get('data_size')]

        if memory_tests:
            memory_ratios = []
            for test in memory_tests:
                data_size_mb = test['data_size'] * 8 * 6 / 1024 / 1024  # Rough estimate
                if data_size_mb > 0:
                    memory_ratio = test['metrics']['memory_delta_mb'] / data_size_mb
                    memory_ratios.append(memory_ratio)

            if memory_ratios:
                efficiency_metrics['memory_efficiency'] = {
                    'avg_memory_ratio': np.mean(memory_ratios),
                    'max_memory_ratio': np.max(memory_ratios),
                    'memory_efficiency_score': max(0, 100 - np.mean(memory_ratios) * 20)  # Lower ratio is better
                }

        # Calculate throughput efficiency
        throughput_tests = [r for r in self.test_results if 'throughput' in r['metrics']]

        if throughput_tests:
            throughputs = [r['metrics']['throughput'] for r in throughput_tests]
            data_sizes = [r.get('data_size', 1000) for r in throughput_tests]

            # Normalize throughput by data size
            normalized_throughputs = []
            for throughput, size in zip(throughputs, data_sizes):
                normalized_throughputs.append(throughput / size * 1000)  # Records per second per 1000 records

            efficiency_metrics['throughput_efficiency'] = {
                'avg_normalized_throughput': np.mean(normalized_throughputs),
                'throughput_consistency': 100 - (np.std(normalized_throughputs) / np.mean(normalized_throughputs) * 100)
                                     if np.mean(normalized_throughputs) > 0 else 0
            }

        return efficiency_metrics

    def _analyze_scalability(self) -> Dict[str, Any]:
        """Analyze scalability characteristics"""
        scalability_analysis = {}

        # Group tests by category and analyze how performance scales with data size
        category_data = {}
        for result in self.test_results:
            category = result['category']
            if category not in category_data:
                category_data[category] = []

            if result.get('data_size') and 'duration' in result['metrics']:
                category_data[category].append({
                    'data_size': result['data_size'],
                    'duration': result['metrics']['duration'],
                    'throughput': result['data_size'] / result['metrics']['duration']
                })

        # Analyze scalability for each category
        for category, data in category_data.items():
            if len(data) >= 3:  # Need at least 3 data points for scaling analysis
                sizes = [d['data_size'] for d in data]
                durations = [d['duration'] for d in data]
                throughputs = [d['throughput'] for d in data]

                # Calculate scaling factors
                size_range = max(sizes) / min(sizes) if min(sizes) > 0 else 1
                duration_range = max(durations) / min(durations) if min(durations) > 0 else 1
                throughput_range = max(throughputs) / min(throughputs) if min(throughputs) > 0 else 1

                # Linear regression to check scaling behavior
                x = np.log(sizes)
                y = np.log(durations)
                coeffs = np.polyfit(x, y, 1)
                scaling_exponent = coeffs[0]  # Close to 1.0 means linear scaling

                scalability_analysis[category] = {
                    'data_size_range': size_range,
                    'duration_range': duration_range,
                    'throughput_range': throughput_range,
                    'scaling_exponent': scaling_exponent,
                    'scalability_score': max(0, 100 - abs(scaling_exponent - 1.0) * 50),  # Closer to 1.0 is better
                    'data_points': len(data)
                }

        return scalability_analysis

    def generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []

        analysis = self.analyze_performance_patterns()
        bottlenecks = analysis.get('bottlenecks', [])
        category_analysis = analysis.get('category_analysis', {})
        efficiency_metrics = analysis.get('efficiency_metrics', {})

        # Recommendations based on bottlenecks
        bottleneck_types = set(b['type'] for b in bottlenecks)

        if 'slow_response_time' in bottleneck_types:
            recommendations.append({
                'category': 'performance_optimization',
                'priority': 'high',
                'title': 'Optimize Slow Response Times',
                'description': 'Several tests show response times significantly above average',
                'actions': [
                    'Implement result caching for frequently accessed data',
                    'Use connection pooling for database operations',
                    'Optimize algorithms and data structures',
                    'Consider lazy loading for large datasets'
                ],
                'expected_improvement': '30-50% reduction in response time'
            })

        if 'high_memory_usage' in bottleneck_types:
            recommendations.append({
                'category': 'memory_optimization',
                'priority': 'high',
                'title': 'Reduce Memory Usage',
                'description': 'Memory usage is excessive in several test scenarios',
                'actions': [
                    'Implement memory pooling and object reuse',
                    'Use generators instead of lists for large datasets',
                    'Optimize data types and reduce memory overhead',
                    'Implement streaming processing for large files'
                ],
                'expected_improvement': '40-60% reduction in memory usage'
            })

        if 'low_throughput' in bottleneck_types:
            recommendations.append({
                'category': 'throughput_optimization',
                'priority': 'medium',
                'title': 'Increase Processing Throughput',
                'description': 'Some operations have lower than expected throughput',
                'actions': [
                    'Implement parallel processing where possible',
                    'Use vectorized operations (NumPy/Pandas)',
                    'Optimize I/O operations and reduce blocking calls',
                    'Batch small operations together'
                ],
                'expected_improvement': '50-100% increase in throughput'
            })

        # Recommendations based on efficiency metrics
        if 'memory_efficiency' in efficiency_metrics:
            mem_eff = efficiency_metrics['memory_efficiency']
            if mem_eff.get('memory_efficiency_score', 100) < 70:
                recommendations.append({
                    'category': 'memory_efficiency',
                    'priority': 'medium',
                    'title': 'Improve Memory Efficiency',
                    'description': f'Memory efficiency score is {mem_eff.get("memory_efficiency_score", 0):.1f}/100',
                    'actions': [
                        f'Reduce memory ratio from {mem_eff.get("avg_memory_ratio", 0):.1f} to < 2.0',
                        'Implement memory-efficient data structures',
                        'Use streaming for large dataset processing'
                    ],
                    'expected_improvement': 'Improve memory efficiency score to > 80'
                })

        # Category-specific recommendations
        for category, data in category_analysis.items():
            if data.get('max_response_time', 0) > 5.0:  # 5 seconds threshold
                recommendations.append({
                    'category': f'{category}_optimization',
                    'priority': 'medium',
                    'title': f'Optimize {category.title()} Performance',
                    'description': f'{category.title()} operations show high variance in response times',
                    'actions': [
                        f'Analyze and optimize slow {category} operations',
                        'Implement performance monitoring and alerting',
                        'Consider architecture improvements for {category}'
                    ],
                    'expected_improvement': f'Reduce max response time in {category} by 50%'
                })

        # General optimization recommendations
        recommendations.extend([
            {
                'category': 'monitoring',
                'priority': 'medium',
                'title': 'Implement Performance Monitoring',
                'description': 'Continuous performance monitoring helps detect issues early',
                'actions': [
                    'Set up automated performance regression testing',
                    'Implement real-time performance dashboards',
                    'Configure performance alerts for key metrics',
                    'Regularly review and update performance baselines'
                ],
                'expected_improvement': 'Early detection of 90% of performance issues'
            },
            {
                'category': 'caching',
                'priority': 'low',
                'title': 'Implement Smart Caching',
                'description': 'Caching can significantly improve performance for repeated operations',
                'actions': [
                    'Cache frequently accessed computed results',
                    'Implement multi-level caching (memory + disk)',
                    'Use cache invalidation strategies',
                    'Consider distributed caching for multi-instance deployments'
                ],
                'expected_improvement': '60-80% improvement for cached operations'
            }
        ])

        self.optimization_recommendations = recommendations
        return recommendations

    def generate_performance_report(self, output_file: str = None) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        analysis = self.analyze_performance_patterns()
        recommendations = self.generate_optimization_recommendations()

        report = {
            'generated_at': datetime.now().isoformat(),
            'test_summary': analysis['summary'],
            'category_analysis': analysis['category_analysis'],
            'performance_trends': analysis['performance_trends'],
            'bottlenecks': analysis['bottlenecks'],
            'efficiency_metrics': analysis['efficiency_metrics'],
            'scalability_analysis': analysis['scalability_analysis'],
            'optimization_recommendations': recommendations,
            'recommendation_summary': {
                'total_recommendations': len(recommendations),
                'high_priority': len([r for r in recommendations if r['priority'] == 'high']),
                'medium_priority': len([r for r in recommendations if r['priority'] == 'medium']),
                'low_priority': len([r for r in recommendations if r['priority'] == 'low'])
            }
        }

        # Save report to file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

        return report


class TestPerformanceReporting:
    """Test performance reporting system"""

    @pytest.fixture
    def performance_analyzer(self):
        """Create performance analyzer instance"""
        return PerformanceAnalyzer()

    @pytest.fixture
    def test_scenarios(self):
        """Define test scenarios for reporting"""
        return [
            {
                'name': 'query_small_dataset',
                'category': 'query',
                'data_size': 1000,
                'metrics': {
                    'duration': 0.05,
                    'throughput': 20000,
                    'memory_delta_mb': 2.1
                }
            },
            {
                'name': 'query_large_dataset',
                'category': 'query',
                'data_size': 100000,
                'metrics': {
                    'duration': 2.5,
                    'throughput': 40000,
                    'memory_delta_mb': 45.2
                }
            },
            {
                'name': 'indicator_calculation',
                'category': 'indicators',
                'data_size': 50000,
                'metrics': {
                    'duration': 1.2,
                    'throughput': 41667,
                    'memory_delta_mb': 15.8
                }
            },
            {
                'name': 'api_single_request',
                'category': 'api',
                'data_size': 1000,
                'metrics': {
                    'duration': 0.15,
                    'throughput': 6667,
                    'memory_delta_mb': 1.2
                }
            },
            {
                'name': 'api_concurrent_requests',
                'category': 'api',
                'data_size': 1000,
                'metrics': {
                    'duration': 3.8,
                    'throughput': 1316,
                    'memory_delta_mb': 8.5
                }
            },
            {
                'name': 'storage_write_operation',
                'category': 'storage',
                'data_size': 50000,
                'metrics': {
                    'duration': 1.8,
                    'throughput': 27778,
                    'memory_delta_mb': 12.3
                }
            },
            {
                'name': 'storage_read_operation',
                'category': 'storage',
                'data_size': 50000,
                'metrics': {
                    'duration': 0.9,
                    'throughput': 55556,
                    'memory_delta_mb': 6.7
                }
            }
        ]

    def test_performance_analysis_generation(self, performance_analyzer, test_scenarios):
        """Test performance analysis generation"""
        # Add test results to analyzer
        for scenario in test_scenarios:
            performance_analyzer.add_test_result(
                test_name=scenario['name'],
                category=scenario['category'],
                metrics=scenario['metrics'],
                data_size=scenario['data_size']
            )

        # Generate analysis
        analysis = performance_analyzer.analyze_performance_patterns()

        # Validate analysis structure
        assert 'summary' in analysis, "Missing summary in analysis"
        assert 'category_analysis' in analysis, "Missing category analysis"
        assert 'bottlenecks' in analysis, "Missing bottlenecks analysis"
        assert 'efficiency_metrics' in analysis, "Missing efficiency metrics"

        # Validate summary
        summary = analysis['summary']
        assert summary['total_tests'] == len(test_scenarios), "Incorrect total test count"
        assert len(summary['categories_tested']) > 0, "No categories tested"
        assert summary['avg_response_time_ms'] > 0, "Average response time should be positive"

        # Validate category analysis
        category_analysis = analysis['category_analysis']
        expected_categories = set(s['category'] for s in test_scenarios)
        actual_categories = set(category_analysis.keys())
        assert actual_categories == expected_categories, f"Category mismatch: {actual_categories} vs {expected_categories}"

        for category, data in category_analysis.items():
            assert data['test_count'] > 0, f"No tests for category {category}"
            assert data['avg_response_time'] > 0, f"Invalid avg response time for {category}"
            assert data['avg_throughput'] > 0, f"Invalid avg throughput for {category}"

        # Validate bottlenecks detection
        bottlenecks = analysis['bottlenecks']
        assert isinstance(bottlenecks, list), "Bottlenecks should be a list"

        return {
            'analysis': analysis,
            'total_categories': len(category_analysis),
            'total_bottlenecks': len(bottlenecks)
        }

    def test_optimization_recommendations(self, performance_analyzer, test_scenarios):
        """Test optimization recommendations generation"""
        # Add test results with some performance issues
        problematic_scenarios = test_scenarios + [
            {
                'name': 'very_slow_query',
                'category': 'query',
                'data_size': 100000,
                'metrics': {
                    'duration': 8.5,  # Very slow
                    'throughput': 11765,
                    'memory_delta_mb': 120.5  # High memory usage
                }
            },
            {
                'name': 'low_throughput_api',
                'category': 'api',
                'data_size': 1000,
                'metrics': {
                    'duration': 5.2,
                    'throughput': 192,  # Very low throughput
                    'memory_delta_mb': 3.1
                }
            }
        ]

        for scenario in problematic_scenarios:
            performance_analyzer.add_test_result(
                test_name=scenario['name'],
                category=scenario['category'],
                metrics=scenario['metrics'],
                data_size=scenario['data_size']
            )

        # Generate recommendations
        recommendations = performance_analyzer.generate_optimization_recommendations()

        # Validate recommendations
        assert len(recommendations) > 0, "Should generate optimization recommendations"
        assert isinstance(recommendations, list), "Recommendations should be a list"

        # Check recommendation structure
        for rec in recommendations:
            assert 'category' in rec, "Missing category in recommendation"
            assert 'priority' in rec, "Missing priority in recommendation"
            assert 'title' in rec, "Missing title in recommendation"
            assert 'description' in rec, "Missing description in recommendation"
            assert 'actions' in rec, "Missing actions in recommendation"
            assert 'expected_improvement' in rec, "Missing expected improvement in recommendation"
            assert rec['priority'] in ['high', 'medium', 'low'], "Invalid priority level"

        # Should have high-priority recommendations for performance issues
        high_priority_count = len([r for r in recommendations if r['priority'] == 'high'])
        assert high_priority_count > 0, "Should have high-priority recommendations for performance issues"

        return {
            'total_recommendations': len(recommendations),
            'high_priority_count': high_priority_count,
            'medium_priority_count': len([r for r in recommendations if r['priority'] == 'medium']),
            'low_priority_count': len([r for r in recommendations if r['priority'] == 'low'])
        }

    def test_performance_report_generation(self, performance_analyzer, test_scenarios, temp_dir):
        """Test comprehensive performance report generation"""
        # Add test results
        for scenario in test_scenarios:
            performance_analyzer.add_test_result(
                test_name=scenario['name'],
                category=scenario['category'],
                metrics=scenario['metrics'],
                data_size=scenario['data_size']
            )

        # Generate report
        report_file = temp_dir / "performance_report.json"
        report = performance_analyzer.generate_performance_report(str(report_file))

        # Validate report structure
        required_sections = [
            'generated_at', 'test_summary', 'category_analysis',
            'performance_trends', 'bottlenecks', 'efficiency_metrics',
            'scalability_analysis', 'optimization_recommendations',
            'recommendation_summary'
        ]

        for section in required_sections:
            assert section in report, f"Missing section: {section}"

        # Validate test summary
        summary = report['test_summary']
        assert summary['total_tests'] == len(test_scenarios), "Incorrect test count in summary"
        assert summary['avg_response_time_ms'] > 0, "Invalid average response time"
        assert summary['avg_throughput'] > 0, "Invalid average throughput"

        # Validate recommendation summary
        rec_summary = report['recommendation_summary']
        assert rec_summary['total_recommendations'] > 0, "Should have recommendations"
        assert rec_summary['high_priority'] + rec_summary['medium_priority'] + rec_summary['low_priority'] == rec_summary['total_recommendations'], "Recommendation count mismatch"

        # Verify report file was created
        assert Path(report_file).exists(), "Report file was not created"
        assert Path(report_file).stat().st_size > 0, "Report file is empty"

        # Validate report file content
        with open(report_file, 'r') as f:
            saved_report = json.load(f)

        assert saved_report == report, "Saved report doesn't match generated report"

        return {
            'report_sections': len([k for k in report.keys() if not k.startswith('_')]),
            'total_recommendations': rec_summary['total_recommendations'],
            'high_priority_recommendations': rec_summary['high_priority'],
            'file_created': True,
            'file_size_bytes': Path(report_file).stat().st_size
        }

    def test_performance_trend_analysis(self, performance_analyzer, temp_dir):
        """Test performance trend analysis over time"""
        # Simulate performance data over time with some trends
        base_time = datetime.now()

        # Add results with improving trend
        for i in range(10):
            # Simulate performance improvement over time
            improvement_factor = 1.0 - (i * 0.05)  # 5% improvement each iteration

            performance_analyzer.add_test_result(
                test_name=f'trend_test_{i}',
                category='query',
                metrics={
                    'duration': 1.0 * improvement_factor,  # Improving
                    'throughput': 10000 / improvement_factor,  # Improving
                    'memory_delta_mb': 10.0 * (1 - i * 0.02)  # Slight improvement
                },
                data_size=5000
            )

        # Add some results with different patterns
        for i in range(5):
            performance_analyzer.add_test_result(
                test_name=f'degradation_test_{i}',
                category='api',
                metrics={
                    'duration': 0.5 * (1 + i * 0.1),  # Degrading
                    'throughput': 5000 / (1 + i * 0.1),  # Degrading
                    'memory_delta_mb': 5.0 * (1 + i * 0.05)  # Slight degradation
                },
                data_size=1000
            )

        # Generate analysis
        analysis = performance_analyzer.analyze_performance_patterns()
        trends = analysis['performance_trends']

        # Validate trend analysis
        assert 'response_time_trend' in trends, "Missing response time trend"
        assert 'throughput_trend' in trends, "Missing throughput trend"
        assert 'memory_trend' in trends, "Missing memory trend"

        # Validate individual trends
        for trend_name, trend_data in trends.items():
            assert 'slope' in trend_data, f"Missing slope in {trend_name}"
            assert 'trend' in trend_data, f"Missing trend in {trend_name}"
            assert 'r_squared' in trend_data, f"Missing r_squared in {trend_name}"

        response_trend = trends['response_time_trend']
        assert response_trend['trend'] == 'decreasing', "Should detect improving response time trend"
        assert response_trend['slope'] < 0, "Response time slope should be negative for improvement"

        throughput_trend = trends['throughput_trend']
        assert throughput_trend['trend'] == 'increasing', "Should detect improving throughput trend"
        assert throughput_trend['slope'] > 0, "Throughput slope should be positive for improvement"

        return {
            'trends_detected': len([t for t in trends.values() if t['trend'] != 'stable']),
            'improving_trends': len([t for t in trends.values() if t['trend'] == 'increasing' or t['trend'] == 'decreasing']),
            'trend_analysis_complete': True
        }

    def test_scalability_analysis(self, performance_analyzer):
        """Test scalability analysis functionality"""
        # Add test results with different data sizes for scalability analysis
        data_sizes = [1000, 5000, 10000, 50000, 100000]

        for size in data_sizes:
            # Simulate near-linear scaling (ideal case)
            duration = size / 20000  # Linear scaling
            throughput = size / duration

            performance_analyzer.add_test_result(
                test_name=f'scalability_test_{size}',
                category='query',
                metrics={
                    'duration': duration,
                    'throughput': throughput,
                    'memory_delta_mb': size * 0.0005  # Linear memory usage
                },
                data_size=size
            )

        # Add some storage tests with different scaling
        storage_sizes = [1000, 10000, 50000, 100000]

        for size in storage_sizes:
            # Storage typically shows super-linear scaling for I/O operations
            duration = (size / 10000) ** 1.2  # Slightly super-linear
            throughput = size / duration

            performance_analyzer.add_test_result(
                test_name=f'storage_scalability_{size}',
                category='storage',
                metrics={
                    'duration': duration,
                    'throughput': throughput,
                    'memory_delta_mb': size * 0.0003
                },
                data_size=size
            )

        # Generate analysis
        analysis = performance_analyzer.analyze_performance_patterns()
        scalability = analysis['scalability_analysis']

        # Validate scalability analysis
        assert len(scalability) > 0, "Should have scalability analysis for at least one category"

        # Check query scalability
        if 'query' in scalability:
            query_scaling = scalability['query']
            assert 'scaling_exponent' in query_scaling, "Missing scaling exponent for query"
            assert 'scalability_score' in query_scaling, "Missing scalability score for query"

            # Should detect near-linear scaling (exponent close to 1.0)
            assert abs(query_scaling['scaling_exponent'] - 1.0) < 0.3, "Query scaling should be near-linear"
            assert query_scaling['scalability_score'] > 70, "Query scalability score should be high"

        # Check storage scalability
        if 'storage' in scalability:
            storage_scaling = scalability['storage']
            assert 'scaling_exponent' in storage_scaling, "Missing scaling exponent for storage"
            assert 'data_size_range' in storage_scaling, "Missing data size range for storage"

            # Should detect the super-linear scaling pattern
            assert storage_scaling['scaling_exponent'] > 1.0, "Storage should show super-linear scaling"

        return {
            'categories_analyzed': len(scalability),
            'query_scalability_score': scalability.get('query', {}).get('scalability_score', 0),
            'storage_scalability_score': scalability.get('storage', {}).get('scalability_score', 0),
            'overall_scalability_health': len([s for s in scalability.values() if s.get('scalability_score', 0) > 70])
        }