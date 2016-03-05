var express = require('express');
var router = express.Router();
var passport = require('passport');
var Account = require('../models/account');

router.use(function(req, res, next) {
  var newHash = req.originalUrl.split('hash/').slice(1)[0];
  req.hash_id = newHash;
  res.contentType('application/json');
  return next();
});

router.all('/pour', function(req, res, next) {
  if(req.user || req.query.anonymous) {
    return res.render('hash/pour', function(err, html) {
      return res.json({
        html: html,
        hash_id: req.hash_id
      });
    });
  } else {
    return res.redirect('/hash/account/login');
  }
});

router.get('/account/login', function(req, res, next) {
  var newHash = req.originalUrl.split('hash/').slice(1)[0];
  Account.find({}).then(function(accounts) {
    return res.render('hash/login', {'users' : accounts }, function(err, html) {
      if(err) {
        return next(err);
      }
      return res.json({
        html : html,
        hash_id: req.hash_id
      });
    });
  });
});

router.post('/account/login', passport.authenticate('local', {
  failureFlash: true,
  failureRedirect: '/hash/account/login'
}), function(req, res) {
  var defaultRedirect = '/hash/account/';
  return res.redirect(req.query.ref || defaultRedirect);
});

router.get('/account/register', function(req, res, next) {
  return res.render('hash/register', function(err, html) {
    if(err) {
      return next(err);
    }
    return res.json({
      html : html,
      hash_id: req.hash_id
    });
  });
});

router.use(function(req, res, next) {
  var err = new Error('Not Found');
  err.status = 404;
  next(err);
});

router.use(function(err, req, res, next) {
  res.status(err.status || 500);
  return res.render('hash/error', {
    message: err.message,
    error: err
  }, function(err, html) {
    return res.json({
      html: html,
      hash_id: req.hash_id
    });
  });
});

module.exports = router;
