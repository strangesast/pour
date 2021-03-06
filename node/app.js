var express = require('express');
var path = require('path');
var favicon = require('serve-favicon');
var logger = require('morgan');
var cookieParser = require('cookie-parser');
var bodyParser = require('body-parser');
var passport = require('passport');
var localStrategy = require('passport-local').Strategy;
var expressSession = require('express-session');
var RedisStore = require('connect-redis')(expressSession);
var flash = require('connect-flash');
var mongoose = require('mongoose');
var config = require('./config');


var app = express();

// view engine setup
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'jade');

// uncomment after placing your favicon in /public
//app.use(favicon(path.join(__dirname, 'public', 'favicon.ico')));
app.use(logger('dev'));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

// redis sessions
var sessionStore = new RedisStore();
app.use(cookieParser(config.secret));
app.use(expressSession({
  secret: config.secret,
  resave: false,
  store: null,
  saveUninitialized: false,
  cookie: {
    expires: true,
    maxAge: 60000
  }
}));
app.use(flash());

// account setup
app.use(passport.initialize());
app.use(passport.session());

var Account = require('./models/account');
passport.use(new localStrategy(Account.authenticate()));
passport.serializeUser(Account.serializeUser());
passport.deserializeUser(Account.deserializeUser());

mongoose.connect(config.databaseUrl, function(err) {
  if (err) {
    console.log("failed to connect to mongo database (" + config.databaseUrl + ")");
  } else {
    console.log("connected to mongodb at " + config.databaseUrl);
  }
  return;
});

var routes = require('./routes/index');
var users = require('./routes/users');
var account = require('./routes/account');
var hash = require('./routes/hash');
var objects = require('./routes/objects');

app.use('/', routes);
app.use('/users', users);
app.use('/account', account);
app.use('/hash', hash);
app.use('/objects', objects);

// catch 404 and forward to error handler
app.use(function(req, res, next) {
  var err = new Error('Not Found');
  err.status = 404;
  next(err);
});

// error handlers

// development error handler
// will print stacktrace
if (app.get('env') === 'development') {
  app.use(function(err, req, res, next) {
    res.status(err.status || 500);
    res.render('error', {
      message: err.message,
      error: err
    });
  });
}

// production error handler
// no stacktraces leaked to user
app.use(function(err, req, res, next) {
  res.status(err.status || 500);
  res.render('error', {
    message: err.message,
    error: {}
  });
});


module.exports = app;
