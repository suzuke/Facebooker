import requests
import pickle
import os
import logging
import time
import json
from requests_toolbelt import MultipartEncoder
from bs4 import BeautifulSoup
try:
    import data_type
    import privacy_level
    import like_action

except ModuleNotFoundError:
    from . import data_type
    from . import privacy_level
    from . import like_action

def letter_adder(string, num):
    if ord(string[1]) + num%26 >= ord('z'):
        string = chr(ord(string[0])+1) + chr(ord(string[1])+ num - 26)
    else:
        string = string[0] + chr(ord(string[1]) + num)
    return string

class API:
    '''
    FB post structure:
        post
        |
        --comment
            |
            --reply
    '''
    def __init__(self):
        headers={
            'scheme': 'https',
            'accept': '*/*',
            'accept-language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6,ja;q=0.5',
            'user-agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:76.0) ' + \
                         'Gecko/20100101 Firefox/76.0',
        }
        self.session = requests.session()
        self.session.headers.update(headers)
        self.login_check = False
    def login(self, email, password):
        # get input field
        self.session.cookies.clear()
        if os.path.isfile(email+'.cookie'):
            self.__load_cookies(email+'.cookie')
        else:
            url = 'https://www.facebook.com/'
            req = self.session.get(url)
            soup = BeautifulSoup(req.text,'lxml')
            all_input_data = soup.find('form').findAll('input')
            data = {}
            for input_data in all_input_data:
                data[input_data.get('name')] = input_data.get('value')
            # input email and password
            data['email'] = email
            data['pass'] = password
            #login
            login_url = 'https://www.facebook.com/login'
            req = self.session.post(login_url,data=data)
        self.user_id = self.session.cookies.get_dict()['c_user']
        # get hidden input data
        url = 'https://m.facebook.com/'
        req = self.session.get(url)
        soup = BeautifulSoup(req.text, 'lxml')
        try:
            self.fb_dtsg = soup.find('input', {'name':'fb_dtsg'}).get('value')
        except Exception as e:
            logging.debug(e)
            logging.error('username or password is invalid')
            return False
        
        self.login_check = True
        self.__save_cookies(email+'.cookie')
        self.send_msg_data = {
                                'fb_dtsg': self.fb_dtsg,
                                'body':'',
                                'send':'傳送',
                                'wwwupp':'C3'
                              }
        self.post_data_template = {
                                    'fb_dtsg': self.fb_dtsg,
                                    'target': self.user_id,
                                    'c_src': 'feed',
                                    'cwevent': 'composer_entry',
                                    'referrer': 'feed',
                                    'ctype': 'inline',
                                    'cver': 'amber',
                                    'rst_icv': None,
                                    'view_post': 'view_post',
                                  }
    def __save_cookies(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def __load_cookies(self, filename):
        with open(filename,'rb') as f:
            self.session.cookies.update(pickle.load(f))
    
    # post methods
    def get_group_post(self, group_id, post_id):
        if not self.login_check:
            logging.error('You should login first')
            return

        url = f'https://m.facebook.com/groups/{group_id}?view=permalink&id={post_id}'
        req = self.session.get(url)
        soup = BeautifulSoup(req.text, 'lxml')
        # divs = soup.findAll('div')
        # for div in divs:
        #     print("*" * 10)
        #     print(div)

        post_content = soup.find('div', class_='bx')
        if not post_content:
            logging.error('This post is not supported or you don\'t have acess authority')
        return post_content


    def get_post(self, post_id):
        if not self.login_check:
            logging.error('You should login first')
            return

        url = f'https://m.facebook.com/story.php?story_fbid={post_id}&id=1'
        req = self.session.get(url)
        soup = BeautifulSoup(req.text,'lxml')
        post_content = soup.find('div',class_='z')
        if not post_content:
            logging.error('This post is not supported or you don\'t have acess authority')
        return post_content

    def like_post(self, post_id, action=like_action.LIKE):

        if not self.login_check:
            logging.error('You should login first')
            return
        if action > 6 or action < 0:
            logging.error('This action is not supported')
            return
        url = f'https://m.facebook.com/reactions/picker/?ft_id={post_id}'
        req = self.session.get(url)
        try:
            soup = BeautifulSoup(req.text, 'lxml')
            root = soup.find('div', id='root').find('table', role='presentation')
            action_href = [a.get('href')  for a in root.findAll('a')][:-1]
            like_url = 'https://m.facebook.com' + action_href[action]
            self.session.get(like_url)
        except:
            logging.error('You don\'t have access authority')

    def get_user_post_list(self, user_id, num=10):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = 'https://m.facebook.com/profile/timeline/stream/?' + \
              'end_time=%s&'%str(time.time()) + \
              'profile_id=%s'%str(user_id)
        posts_id = []
        while len(posts_id) < num:
            req = self.session.get(url)
            soup = BeautifulSoup(req.text, 'lxml')
            posts = soup.find('section').findAll('article', recursive=False)
            for post in posts:
                data = json.loads(post.get('data-ft'))
                post_id = data['mf_story_key']
                posts_id.append(post_id)
                if len(posts_id) >= num:
                    break
            if len(posts_id) >= num:
                    break
            next_href = soup.find('div', id='u_0_0').find('a').get('href')
            url = 'https://m.facebook.com' + next_href
        return posts_id

    def get_group_post_list(self, group_id, num=10):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = 'https://m.facebook.com/%s'%str(group_id)
        posts_id = []
        while len(posts_id) < num:
            req = self.session.get(url)
            soup = BeautifulSoup(req.text, 'lxml')
            posts = soup.find('div', id='m_group_stories_container').find('section').findAll('article',recursive=False)
            for post in posts:
                data = json.loads(post.get('data-ft'))
                post_id = data['mf_story_key']
                posts_id.append(post_id)
                if len(posts_id) >= num:
                    break
            if len(posts_id) >= num:
                    break
            next_href = soup.find('div', id='m_group_stories_container').find('div', class_='dz ea eb ec ed').find('a').get('href')
            url = 'https://m.facebook.com' + next_href
        return posts_id
    
    def get_fanpage_post_list(self, fanpage_id, num=10):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = 'https://m.facebook.com/%s'%str(fanpage_id)
        posts_id = []
        while len(posts_id) < num:
            req = self.session.get(url)
            soup = BeautifulSoup(req.text, 'lxml')
            posts = soup.find('section').findAll('article', recursive=False)
            for post in posts:
                data = json.loads(post.get('data-ft'))
                post_id = data['mf_story_key']
                posts_id.append(post_id)
                if len(posts_id) >= num:
                    break
            if len(posts_id) >= num:
                    break
            next_href = soup.find('div', id='recent').next_sibling.find('a').get('href')
            url = 'https://m.facebook.com' + next_href
        return posts_id

    def post(self, 
             content, 
             privacy_level=privacy_level.PUBLIC):
        if not self.login_check:
            logging.error('You should login first')
            return
        post_data = self.post_data_template
        url = 'https://m.facebook.com/composer/mbasic/'
        post_data['xc_message'] = content
        post_data['privacyx'] = privacy_level
        self.session.post(url, data=post_data)

    def post_to_target(self, content, target_id=None, target_type=None):
        ''' target_type:
                0 : user
                1 : group
                2 : fanpage
        '''
        if not self.login_check:
            logging.error('You should login first')
            return
        referrer = ['timeline', 'group', 'pages_feed']
        c_src = ['timeline_other', 'group', 'page_self']
        post_data = self.post_data_template
        url = 'https://m.facebook.com/composer/mbasic/'
        post_data['xc_message'] = content
        post_data['referrer'] = referrer[target_type]
        post_data['c_src'] = c_src[target_type]
        post_data['target'] = target_id
        post_data['id'] = target_id
        self.session.post(url, data=post_data)

    def fanpage_post(self, content, fanpage_id):
        if not self.login_check:
            logging.error('You should login first')
            return
        post_data = self.post_data_template
        url = 'https://m.facebook.com/composer/mbasic/?av=%s'%str(fanpage_id)
        post_data['xc_message'] = content
        post_data['referrer'] = 'pages_feed'
        post_data['c_src'] = 'page_self'
        post_data['target'] = fanpage_id
        self.session.post(url, data=post_data)

    def fanpage_post_photo(self, text_content, image, fanpage_id):
        url = 'https://m.facebook.com/composer/mbasic/' + \
                        '?c_src=page_self&referrer=pages_feed&' + \
                        'target=%s&'%fanpage_id + \
                        'icv=lgc_view_photo&av=%s'%fanpage_id
        req = self.session.get(url)
        soup = BeautifulSoup(req.text,'lxml')
        form = soup.find('form')
        all_input_data = form.findAll('input')
        data = {}
        for input_data in all_input_data:
            data[input_data.get('name')] = input_data.get('value')

        url = 'https://upload.facebook.com/_mupload_/composer/?av=%s'%fanpage_id
        data['file1'] = ('image',image,'image')
        data['xc_message'] = text_content
        m_data = MultipartEncoder(
                        fields = data
                 )
        self.session.post(url, data=m_data, headers={'Content-Type': m_data.content_type})

    # comment methods
    def get_comments(self, post_id, num=10, start=0):
        if not self.login_check:
            logging.error('You should login first')
            return
        
        comment_info_list = []
        while num > 0:
            url = 'https://m.facebook.com/story.php?' + \
                'story_fbid=%s&id=1&p=%s'%(str(post_id),start)
            req = self.session.get(url)
            soup = BeautifulSoup(req.text,'lxml')
            try:
                div = soup.find('div',id='ufi_%s'%str(post_id))
                comment_div = div.find('div',id='sentence_%s'%str(post_id)).next_sibling.next_sibling
                comments = comment_div.findAll('div', recursive=False)
                comments.reverse()
            except Exception as e:
                logging.debug(e)
                logging.error('You don\'t have access authority')
                return

            for comment in comments:
                try:
                    comment_author = comment.find('h3').find('a').text
                    comment_id = comment.get('id')
                    comment_content = comment.find('h3').next_sibling.text
                    comment_time = comment.find('abbr').text
                    comment_info = data_type.comment_info(comment_id,
                                                          comment_author,
                                                          comment_content,
                                                          comment_time
                                                         )
                    comment_info_list.append(comment_info)
                    num -= 1
                except:
                    pass

            # pre_page_div = comment_div.find('div', id='see_prev_%s'%str(post_id))
            #
            # if pre_page_div:
            #     pre_href = pre_page_div.find('a').get('href')
            #     pre_href = pre_href[pre_href.find('p='):]
            #     start = pre_href[2:pre_href.find('&')]
            # else:
            #     break

            next_page_div = comment_div.find('div', id='see_next_%s'%str(post_id))

            if next_page_div:
                next_href = next_page_div.find('a').get('href')
                next_href = next_href[next_href.find('p='):]
                start = next_href[2:next_href.find('&')]
            else:
                break

        return comment_info_list

    def delete_comment(self, post_id, comment_id):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = 'https://m.facebook.com/ufi/delete/?' + \
              'delete_comment_id=%s'%str(comment_id) + \
              '&delete_comment_fbid=%s'%str(comment_id) + \
              '&ft_ent_identifier=%s'%str(post_id)
        data = {'fb_dtsg': self.fb_dtsg}
        return self.session.post(url, data=data)

    def comment(self, post_id, content):
        url = 'https://m.facebook.com/a/comment.php?' + \
              'fs=8&actionsource=2&comment_logging' + \
              '&ft_ent_identifier=%s'%str(post_id)
        comment = {'comment_text':content,'fb_dtsg':self.fb_dtsg}
        return self.session.post(url, data=comment)

    # reply method
    def reply(self, post_id ,comment_id, content):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = 'https://m.facebook.com/a/comment.php?' + \
              'parent_comment_id=%s'%str(comment_id) + \
              '&ft_ent_identifier=%s'%str(post_id)
        data = {'fb_dtsg': self.fb_dtsg, 'comment_text':content}
        self.session.post(url, data=data)

    # messenger method
    def get_msg(self, chat_room_id, num=1):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = 'https://m.facebook.com/messages/read/?tid=%s'%str(chat_room_id)
        send_from = []
        content = []
        time = []
        while num > 0:
            req = self.session.get(url)
            soup = BeautifulSoup(req.text, 'lxml')
            msg_group = soup.find('div', id='messageGroup')
            if len(msg_group) == 1:
                index = 0
            else:
                index = 1
            
            msgs = msg_group.findAll('div', recursive=False)[index].findAll('div', recursive=False)
            if msgs:
                msgs.reverse()
            for msg in msgs:
                content_class = letter_adder(msg.get('class')[-1], 1)
                try:
                    msg_contents = msg.find('div', class_=content_class). \
                                                        find('div').findAll('span')
                    for msg_content in msg_contents:
                        send_from.append(msg.find('strong').text)
                        content.append(msg_content.text)
                        time.append(msg.find('abbr').text)
                        num -= 1
                        if num <= 0:
                            break
                    if num <= 0:
                        break
                except:
                    logging.debug('Get non text message')
                    pass
            pre_page = msg_group.find('div', id='see_older')
            if not pre_page:
                break
            href = pre_page.find('a').get('href')
            url = 'https://m.facebook.com' + href

        return list(zip(send_from, content, time))

    def get_unread_chat(self):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = 'https://m.facebook.com/messages/?folder=unread'
        req = self.session.get(url)
        soup = BeautifulSoup(req.text, 'lxml')
        unread_chats = soup.find('div', id='root').find('section').findAll('table')
        unread_chat_room_id = []
        for unread_chat in unread_chats:
            href = unread_chat.find('a').get('href')
            if href.find('cid.c') >= 0:
                chat_room_id = href[href.find('cid.c.')+6:href.find('%')]
                if chat_room_id == self.user_id:
                    chat_room_id = href[href.find('%')+3:href.find('&')]
            else:
                chat_room_id = href[href.find('cid.g.')+6:href.find('&')]
            unread_chat_room_id.append(chat_room_id)
        
        return unread_chat_room_id

    def send_msg(self, chat_room_id, content):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = 'https://m.facebook.com/messages/send/'
        if len(str(chat_room_id)) > len(self.user_id):
            self.send_msg_data['tids'] = 'cid.g.%s'%str(chat_room_id)
        else:
            self.send_msg_data['tids'] = '%s'%str(chat_room_id)
            self.send_msg_data['ids[%s]'%str(chat_room_id)] = str(chat_room_id)
        self.send_msg_data['body'] = content
        self.session.post(url, data=self.send_msg_data)

    #group
    def get_group_member_list(self, group_id, num=10):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = f'https://m.facebook.com/browse/group/members/?id={group_id}&start=0&listType=list_general'

        members_id = set()
        while len(members_id) < num:
            #print(url)
            req = self.session.get(url)
            soup = BeautifulSoup(req.text, 'lxml')
            members = soup.findAll('table', id=lambda x: x and x.startswith('member_'))
            for member in members:
                try:
                    member_id = member.get('id').replace('member_', '')
                    members_id.add(member_id)
                except:
                    pass
                if len(members_id) == num:
                    break
            #print(len(members_id))
            try:
                next_href = soup.find('div', id='m_more_item').find('a').get('href')
            except AttributeError:
                logging.error('The maximum number is 120 due to facebook\'s limitation.')
                break
            url = f'https://m.facebook.com{next_href}'
        return [member_id for member_id in members_id]

    #profile
    def get_user_about(self, user_id):
        if not self.login_check:
            logging.error('You should login first')
            return
        url = f'https://m.facebook.com/{user_id}'
        req = self.session.get(url)
        user_name = req.url.replace('https://m.facebook.com/', '').replace('?_rdr', '')
        about_url = f'https://m.facebook.com/{user_name}/about'
        print(about_url)
        req = self.session.get(about_url)
        soup = BeautifulSoup(req.text, 'lxml')
        print(soup)
