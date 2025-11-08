#!/usr/bin/env node

'use strict';

const https = require('node:https');
const { URL } = require('node:url');

const DEFAULT_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/json',
  'Accept-Language': 'en-US,en;q=0.9',
  'Accept-Encoding': 'identity'
};

async function fetchText(url, headers = {}, redirectCount = 0) {
  const MAX_REDIRECTS = 5;
  if (redirectCount > MAX_REDIRECTS) {
    throw new Error('Too many redirects while requesting ' + url);
  }

  const urlObj = new URL(url);
  const requestHeaders = { ...DEFAULT_HEADERS, ...headers };

  return new Promise((resolve, reject) => {
    const options = {
      method: 'GET',
      headers: requestHeaders
    };

    const req = https.request(urlObj, options, (res) => {
      const statusCode = res.statusCode || 0;
      const location = res.headers.location;

      if (statusCode >= 300 && statusCode < 400 && location) {
        const redirectUrl = new URL(location, urlObj).toString();
        res.resume();
        fetchText(redirectUrl, headers, redirectCount + 1).then(resolve).catch(reject);
        return;
      }

      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => {
        if (statusCode >= 200 && statusCode < 300) {
          resolve(body);
        } else {
          const error = new Error(`Request failed with status ${statusCode}`);
          error.statusCode = statusCode;
          error.body = body;
          reject(error);
        }
      });
    });

    req.on('error', reject);
    req.end();
  });
}

function extractJsonPayload(html, marker) {
  const markerIndex = html.indexOf(marker);
  if (markerIndex === -1) {
    return null;
  }

  let index = markerIndex + marker.length;
  while (index < html.length && html[index] !== '{' && html[index] !== '[') {
    index += 1;
  }

  if (index >= html.length) {
    return null;
  }

  const openChar = html[index];
  const closeChar = openChar === '{' ? '}' : ']';
  let depth = 0;
  let inString = false;
  let escapeNext = false;

  for (let i = index; i < html.length; i += 1) {
    const char = html[i];

    if (inString) {
      if (escapeNext) {
        escapeNext = false;
      } else if (char === '\\') {
        escapeNext = true;
      } else if (char === '"') {
        inString = false;
      }
    } else {
      if (char === '"') {
        inString = true;
      } else if (char === openChar) {
        depth += 1;
      } else if (char === closeChar) {
        depth -= 1;
        if (depth === 0) {
          return html.slice(index, i + 1);
        }
      }
    }
  }

  return null;
}

function extractUsingMarkers(html, markers) {
  for (const marker of markers) {
    const payload = extractJsonPayload(html, marker);
    if (payload) {
      return payload;
    }
  }
  return null;
}

function traverseAndCollectVideoRenderers(node, collector) {
  if (!node) {
    return;
  }

  if (Array.isArray(node)) {
    node.forEach((item) => traverseAndCollectVideoRenderers(item, collector));
    return;
  }

  if (typeof node === 'object') {
    if (node.videoRenderer) {
      collector.push(node.videoRenderer);
    }

    for (const value of Object.values(node)) {
      traverseAndCollectVideoRenderers(value, collector);
    }
  }
}

function textFromRuns(runs) {
  if (!runs) {
    return '';
  }
  return runs.map((run) => run.text).join('');
}

function parseViewCount(viewText) {
  if (!viewText || typeof viewText !== 'string') {
    return null;
  }

  const normalized = viewText.replace(/[,\s]/g, '').toUpperCase();
  const units = [
    { suffix: '億', multiplier: 1e8 },
    { suffix: '万', multiplier: 1e4 },
    { suffix: '萬', multiplier: 1e4 },
    { suffix: 'K', multiplier: 1e3 },
    { suffix: 'M', multiplier: 1e6 },
    { suffix: 'B', multiplier: 1e9 }
  ];

  const unitMatch = units.find(({ suffix }) => normalized.includes(suffix));
  if (unitMatch) {
    const numberPart = normalized.split(unitMatch.suffix)[0];
    const value = parseFloat(numberPart);
    if (!Number.isNaN(value)) {
      return Math.round(value * unitMatch.multiplier);
    }
  }

  const digits = normalized.replace(/[^0-9]/g, '');
  if (!digits) {
    return null;
  }
  return parseInt(digits, 10);
}

function parseVideoRenderer(videoRenderer) {
  const videoId = videoRenderer.videoId;
  const title = textFromRuns(videoRenderer.title?.runs) || videoRenderer.title?.simpleText;
  const channelName = textFromRuns(videoRenderer.ownerText?.runs);
  const channelId = videoRenderer.ownerText?.runs?.[0]?.navigationEndpoint?.browseEndpoint?.browseId;
  const description = textFromRuns(videoRenderer.detailedMetadataSnippets?.[0]?.snippetText?.runs) || textFromRuns(videoRenderer.descriptionSnippet?.runs);
  const viewCountText = videoRenderer.viewCountText?.simpleText || textFromRuns(videoRenderer.viewCountText?.runs);
  const publishedTimeText = videoRenderer.publishedTimeText?.simpleText || textFromRuns(videoRenderer.publishedTimeText?.runs);
  const lengthText = videoRenderer.lengthText?.simpleText || textFromRuns(videoRenderer.lengthText?.runs);
  const badges = (videoRenderer.badges || []).map((badge) => badge.metadataBadgeRenderer?.label).filter(Boolean);

  return {
    videoId,
    title,
    channelName,
    channelId,
    description,
    viewCountText,
    viewCount: parseViewCount(viewCountText),
    publishedTimeText,
    lengthText,
    badges
  };
}

async function getSearchResults(keyword, options = {}) {
  const {
    regionCode = 'US',
    languageCode = 'en',
    resultLimit = 5
  } = options;

  const searchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(keyword)}&hl=${encodeURIComponent(languageCode)}&gl=${encodeURIComponent(regionCode)}`;
  const html = await fetchText(searchUrl);
  const jsonPayload = extractUsingMarkers(html, [
    'var ytInitialData =',
    'window["ytInitialData"] =',
    'ytInitialData ='
  ]);
  if (!jsonPayload) {
    throw new Error('Unable to locate search metadata (ytInitialData).');
  }

  const searchData = JSON.parse(jsonPayload);
  const renderers = [];
  traverseAndCollectVideoRenderers(searchData, renderers);
  const videos = renderers
    .map(parseVideoRenderer)
    .filter((video) => Boolean(video.videoId))
    .slice(0, resultLimit);

  const relatedSearches = Array.isArray(searchData.refinements) ? searchData.refinements.slice() : [];

  return { videos, relatedSearches };
}

async function getVideoDetails(videoId, options = {}) {
  const {
    regionCode = 'US',
    languageCode = 'en'
  } = options;

  const watchUrl = `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}&hl=${encodeURIComponent(languageCode)}&gl=${encodeURIComponent(regionCode)}`;

  try {
    const html = await fetchText(watchUrl);
    const jsonPayload = extractUsingMarkers(html, [
      'var ytInitialPlayerResponse =',
      'window["ytInitialPlayerResponse"] =',
      'ytInitialPlayerResponse ='
    ]);
    if (!jsonPayload) {
      return { keywords: [] };
    }
    const playerResponse = JSON.parse(jsonPayload);
    const videoDetails = playerResponse.videoDetails || {};
    return {
      title: videoDetails.title,
      keywords: Array.isArray(videoDetails.keywords) ? videoDetails.keywords : [],
      author: videoDetails.author
    };
  } catch (error) {
    return { keywords: [], error: error.message };
  }
}

async function getKeywordSuggestions(keyword, options = {}) {
  const {
    languageCode = 'en'
  } = options;

  const suggestionUrl = `https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl=${encodeURIComponent(languageCode)}&q=${encodeURIComponent(keyword)}`;
  const responseText = await fetchText(suggestionUrl, {
    Accept: 'application/json'
  });

  try {
    const parsed = JSON.parse(responseText);
    if (Array.isArray(parsed) && parsed.length > 1 && Array.isArray(parsed[1])) {
      return parsed[1];
    }
    return [];
  } catch (error) {
    return [];
  }
}

async function getTrendingVideos(options = {}) {
  const {
    regionCode = 'US',
    languageCode = 'en',
    limit = 10
  } = options;

  const trendingUrl = `https://www.youtube.com/feed/trending?gl=${encodeURIComponent(regionCode)}&hl=${encodeURIComponent(languageCode)}`;
  const html = await fetchText(trendingUrl);
  const jsonPayload = extractUsingMarkers(html, [
    'var ytInitialData =',
    'window["ytInitialData"] =',
    'ytInitialData ='
  ]);
  if (!jsonPayload) {
    throw new Error('Unable to locate trending metadata (ytInitialData).');
  }

  const trendingData = JSON.parse(jsonPayload);
  const renderers = [];
  traverseAndCollectVideoRenderers(trendingData, renderers);
  const videos = renderers
    .map(parseVideoRenderer)
    .filter((video) => Boolean(video.videoId))
    .slice(0, limit);

  return videos;
}

function aggregateTrendingKeywords(trendingVideos, options = {}) {
  const {
    keywordLimit = 20
  } = options;

  const frequency = new Map();

  for (const video of trendingVideos) {
    const contributions = [];
    if (Array.isArray(video.keywords) && video.keywords.length > 0) {
      contributions.push(...video.keywords);
    }

    const title = video.title || '';
    contributions.push(...title
      .split(/[\s\-_,!！?？:：\(\)\[\]\{\}\|\/]+/)
      .map((token) => token.trim())
      .filter((token) => token.length >= 2));

    for (const token of contributions) {
      const normalized = token.trim();
      if (!normalized) {
        continue;
      }
      const current = frequency.get(normalized) || 0;
      frequency.set(normalized, current + 1);
    }
  }

  return Array.from(frequency.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, keywordLimit)
    .map(([token, count]) => ({ keyword: token, occurrences: count }));
}

async function enrichVideosWithDetails(videos, options = {}) {
  const enriched = [];
  for (const video of videos) {
    const details = await getVideoDetails(video.videoId, options);
    enriched.push({
      ...video,
      keywords: details.keywords,
      detailTitle: details.title,
      detailAuthor: details.author
    });
  }
  return enriched;
}

async function analyzeKeyword(keyword, options = {}) {
  if (!keyword || typeof keyword !== 'string') {
    throw new Error('A keyword string must be provided.');
  }

  const {
    regionCode = 'US',
    languageCode = 'en',
    searchResultLimit = 5,
    trendingLimit = 10,
    trendingKeywordLimit = 20
  } = options;

  const [suggestions, searchResults] = await Promise.all([
    getKeywordSuggestions(keyword, { languageCode }),
    getSearchResults(keyword, { regionCode, languageCode, resultLimit: searchResultLimit })
  ]);

  const enrichedTopVideos = await enrichVideosWithDetails(searchResults.videos, { regionCode, languageCode });

  const bestVideo = enrichedTopVideos.reduce((currentBest, candidate) => {
    if (!currentBest) {
      return candidate;
    }

    const currentViews = currentBest.viewCount || -1;
    const candidateViews = candidate.viewCount || -1;
    if (candidateViews > currentViews) {
      return candidate;
    }
    return currentBest;
  }, null);

  const trendingVideos = await getTrendingVideos({ regionCode, languageCode, limit: trendingLimit });
  const trendingSample = await enrichVideosWithDetails(trendingVideos.slice(0, Math.min(5, trendingVideos.length)), { regionCode, languageCode });

  const aggregatedTrendingKeywords = aggregateTrendingKeywords(trendingSample, { keywordLimit: trendingKeywordLimit });
  const trendingResults = trendingVideos.map((video) => {
    const enriched = trendingSample.find((item) => item.videoId === video.videoId);
    return enriched || video;
  });

  return {
    keyword,
    regionCode,
    languageCode,
    generatedAt: new Date().toISOString(),
    suggestions,
    relatedSearches: searchResults.relatedSearches,
    topVideos: enrichedTopVideos,
    bestVideo,
    trending: {
      videos: trendingResults,
      hotKeywords: aggregatedTrendingKeywords
    }
  };
}

function parseArguments(argv) {
  const args = {
    keyword: '',
    regionCode: 'US',
    languageCode: 'en',
    searchResultLimit: 5,
    trendingLimit: 10,
    trendingKeywordLimit: 20
  };

  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    switch (arg) {
      case '-k':
      case '--keyword':
        args.keyword = argv[++i] || '';
        break;
      case '--region':
        args.regionCode = (argv[++i] || '').toUpperCase();
        break;
      case '--language':
        args.languageCode = argv[++i] || 'en';
        break;
      case '--results':
        args.searchResultLimit = parseInt(argv[++i], 10) || args.searchResultLimit;
        break;
      case '--trending':
        args.trendingLimit = parseInt(argv[++i], 10) || args.trendingLimit;
        break;
      case '--hot-keywords':
        args.trendingKeywordLimit = parseInt(argv[++i], 10) || args.trendingKeywordLimit;
        break;
      case '-h':
      case '--help':
        return { ...args, help: true };
      default:
        if (!args.keyword) {
          args.keyword = arg;
        }
        break;
    }
  }

  return args;
}

function printHelp() {
  const usage = `YouTube Keyword Insights\n\n` +
    `Usage: node youtube_insights.js --keyword <keyword> [options]\n\n` +
    `Options:\n` +
    `  -k, --keyword <value>          Keyword to analyze.\n` +
    `      --region <code>           Two-letter region code (default: US).\n` +
    `      --language <code>         UI language code (default: en).\n` +
    `      --results <number>        Number of top videos to analyze (default: 5).\n` +
    `      --trending <number>       Number of trending videos to fetch (default: 10).\n` +
    `      --hot-keywords <number>   Number of hot keywords to return (default: 20).\n` +
    `  -h, --help                    Show this help message.\n` +
    `\nExample:\n` +
    `  node youtube_insights.js --keyword "旅行 vlog" --region TW --language zh-TW\n`;

  console.log(usage);
}

if (require.main === module) {
  (async () => {
    const args = parseArguments(process.argv);
    if (args.help || !args.keyword) {
      printHelp();
      if (!args.help && !args.keyword) {
        process.exitCode = 1;
      }
      return;
    }

    try {
      const result = await analyzeKeyword(args.keyword, {
        regionCode: args.regionCode,
        languageCode: args.languageCode,
        searchResultLimit: args.searchResultLimit,
        trendingLimit: args.trendingLimit,
        trendingKeywordLimit: args.trendingKeywordLimit
      });
      console.log(JSON.stringify(result, null, 2));
    } catch (error) {
      console.error('Failed to analyze keyword:', error.message);
      process.exitCode = 1;
    }
  })();
}

module.exports = {
  analyzeKeyword,
  getTrendingVideos,
  getKeywordSuggestions,
  getSearchResults
};
